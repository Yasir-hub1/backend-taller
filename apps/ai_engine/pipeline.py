"""
Orquesta el procesamiento asíncrono de un incidente recién creado.
Se ejecuta via django-q2 en background.
"""
from apps.ai_engine.whisper_service import WhisperService
from apps.ai_engine.classifier_service import IncidentClassifier
from apps.ai_engine.summary_service import SummaryService
from apps.incidents.models import Incident, Evidence, EvidenceType, IncidentType, IncidentPriority, IncidentStatus


# Mapeo de tipo de incidente a prioridad
PRIORITY_MAP = {
    'accident': IncidentPriority.HIGH,
    'engine': IncidentPriority.HIGH,
    'overheating': IncidentPriority.HIGH,
    'battery': IncidentPriority.MEDIUM,
    'tire': IncidentPriority.MEDIUM,
    'locksmith': IncidentPriority.LOW,
    'other': IncidentPriority.LOW,
    'uncertain': IncidentPriority.MEDIUM,
}


def process_incident_pipeline(incident_id: int):
    """
    Función principal ejecutada por django-q2.

    Proceso:
    1. Marca incidente como 'analyzing'
    2. Procesa evidencias de audio (Whisper)
    3. Procesa evidencias de imagen (TensorFlow)
    4. Determina tipo y prioridad
    5. Genera resumen con GPT
    6. Actualiza incidente
    7. Dispara motor de asignación
    """
    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        print(f"Incident {incident_id} not found")
        return

    # Cambiar estado a analyzing
    incident.status = IncidentStatus.ANALYZING
    incident.save(update_fields=['status'])

    # Inicializar servicios IA
    whisper = WhisperService()
    classifier = IncidentClassifier()
    summary_svc = SummaryService()

    transcriptions = []
    best_classification = {'label': 'uncertain', 'confidence': 0.0}

    # Procesar evidencias
    for evidence in incident.evidences.all():
        if evidence.evidence_type == EvidenceType.AUDIO and not evidence.transcription_done:
            result = whisper.transcribe(evidence.file.path)
            if result['success']:
                evidence.transcription = result['transcription']
                evidence.transcription_done = True
                evidence.save()
                transcriptions.append(result['transcription'])

        elif evidence.evidence_type == EvidenceType.IMAGE:
            result = classifier.predict(evidence.file.path)
            evidence.image_analysis = result
            evidence.label = result.get('label', '')
            evidence.save()
            if result.get('confidence', 0) > best_classification['confidence']:
                best_classification = result

    # Determinar tipo de incidente basado en clasificación de imagen
    if best_classification['confidence'] > 0.5:
        incident_type = best_classification['label']
    else:
        incident_type = 'uncertain'

    # Validar que el tipo esté en las opciones válidas
    valid_types = [choice[0] for choice in IncidentType.choices]
    if incident_type not in valid_types:
        incident_type = IncidentType.OTHER

    # Preparar datos del vehículo para el resumen
    vehicle_info = {}
    if incident.vehicle:
        vehicle_info = {
            'brand': incident.vehicle.brand,
            'model': incident.vehicle.model,
            'year': incident.vehicle.year
        }

    # Generar resumen GPT
    summary_json = summary_svc.generate_summary({
        'transcription': ' '.join(transcriptions),
        'classification': incident_type,
        'confidence': best_classification.get('confidence', 0),
        'description': incident.description,
        'vehicle': vehicle_info,
        'address': incident.address_text,
    })

    # Actualizar incidente con resultados
    incident.incident_type = incident_type
    incident.ai_transcription = ' '.join(transcriptions)
    incident.ai_classification_raw = best_classification
    incident.ai_summary = summary_json
    incident.ai_confidence = best_classification.get('confidence', 0)
    incident.priority = PRIORITY_MAP.get(incident_type, IncidentPriority.MEDIUM)
    incident.status = IncidentStatus.WAITING_WORKSHOP
    incident.save()

    # Disparar motor de asignación
    try:
        from apps.assignments.engine import AssignmentEngine
        AssignmentEngine.find_and_notify_workshops(incident)
    except Exception as e:
        print(f"Error in assignment engine: {e}")

    print(f"Incident {incident_id} processed successfully")
