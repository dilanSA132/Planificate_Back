from typing import List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.Trip import Trip
from models.POI import POI
from models.ItineraryItem import ItineraryItem
from schemas import ItineraryItemWrite, ItineraryItemRead, TripSchedule, ScheduleDay, ScheduleActivity, FreeTimeSlot, POIRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/itinerary", tags=["Itinerary"])


@router.post("/", response_model=ItineraryItemRead, status_code=status.HTTP_201_CREATED)
def create_item(trip_id: int, payload: ItineraryItemWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    poi = None
    if payload.poi_id:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if not poi:
            raise HTTPException(status_code=404, detail="POI no existe en este trip")

    item = ItineraryItem(**payload.model_dump())
    db.add(item)
    db.flush()  # Flush para obtener el ID del item
    
    # Si el item tiene un POI y un start_ts, actualizar el scheduled_at del POI
    # Esto es equivalente a programar el POI directamente desde el mapa
    if payload.poi_id and payload.start_ts and poi:
        poi.scheduled_at = payload.start_ts
        # Actualizar duration_minutes basado en la duración del ItineraryItem
        # Siempre actualizar, no solo si está vacío, para mantener sincronización
        if payload.end_ts and payload.start_ts:
            duration_seconds = (payload.end_ts - payload.start_ts).total_seconds()
            poi.duration_minutes = int(duration_seconds / 60)
    
    db.commit()
    db.refresh(item)
    # Refrescar también el POI para asegurar que los cambios se reflejen
    if poi:
        db.refresh(poi)
    return item


@router.get("/", response_model=List[ItineraryItemRead])
def list_items(trip_id: int, db: Session = Depends(get_db)):
    return db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()


@router.put("/{item_id}", response_model=ItineraryItemRead)
def update_item(trip_id: int, item_id: int, payload: ItineraryItemWrite, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")

    # Guardar el POI anterior para limpiar su scheduled_at si es necesario
    old_poi_id = item.poi_id

    if payload.poi_id:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if not poi:
            raise HTTPException(status_code=404, detail="POI no existe en este trip")

    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="No se puede mover el ítem a otro trip desde este endpoint")

    for k, v in payload.model_dump().items():
        setattr(item, k, v)

    # Si el item tiene un POI y un start_ts, actualizar el scheduled_at del POI
    # Esto es equivalente a programar el POI directamente desde el mapa
    if payload.poi_id and payload.start_ts:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if poi:
            poi.scheduled_at = payload.start_ts
            # Actualizar duration_minutes basado en la duración del ItineraryItem
            # Siempre actualizar, no solo si está vacío, para mantener sincronización
            if payload.end_ts and payload.start_ts:
                duration_seconds = (payload.end_ts - payload.start_ts).total_seconds()
                poi.duration_minutes = int(duration_seconds / 60)
    elif old_poi_id and old_poi_id != payload.poi_id:
        # Si se cambió el POI, limpiar el scheduled_at del POI anterior si no hay más items
        old_poi = db.query(POI).filter_by(id=old_poi_id, trip_id=trip_id).first()
        if old_poi:
            # Verificar si hay otros ItineraryItems asociados a este POI
            other_items = db.query(ItineraryItem).filter(
                ItineraryItem.poi_id == old_poi_id,
                ItineraryItem.id != item_id,
                ItineraryItem.start_ts.isnot(None)
            ).first()
            if not other_items:
                old_poi.scheduled_at = None

    db.commit()
    db.refresh(item)
    # Refrescar también el POI si se actualizó
    if payload.poi_id and payload.start_ts:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if poi:
            db.refresh(poi)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(trip_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    
    # Si el item tiene un POI asociado, verificar si hay otros items antes de eliminar el POI
    poi_id = item.poi_id
    
    # Guardar el POI antes de eliminar el item
    poi = None
    if poi_id:
        poi = db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first()
    
    # Eliminar el ItineraryItem
    db.delete(item)
    db.flush()  # Flush para asegurar que el item se elimine antes de verificar otros items
    
    # Si hay un POI asociado, verificar si hay otros ItineraryItems con este POI
    if poi_id and poi:
        # Verificar si hay otros ItineraryItems asociados a este POI
        other_items_count = db.query(ItineraryItem).filter(
            ItineraryItem.poi_id == poi_id
        ).count()
        
        if other_items_count == 0:
            # No hay más ItineraryItems asociados a este POI, eliminar el POI completamente
            db.delete(poi)
        else:
            # Hay otros items, solo limpiar el scheduled_at si no hay items programados
            items_with_schedule_count = db.query(ItineraryItem).filter(
                ItineraryItem.poi_id == poi_id,
                ItineraryItem.start_ts.isnot(None)
            ).count()
            
            if items_with_schedule_count == 0:
                # No hay más items programados, limpiar el scheduled_at del POI
                poi.scheduled_at = None
    
    db.commit()


@router.get("/schedule", response_model=TripSchedule)
def get_schedule(trip_id: int, db: Session = Depends(get_db)):
    """
    Get combined schedule for a trip, including POIs and ItineraryItems.
    Groups activities by day and detects free time slots.
    """
    # Verify trip exists
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip no existe")
    
    # Get all POIs with scheduled_at
    scheduled_pois = db.query(POI).filter(
        POI.trip_id == trip_id,
        POI.scheduled_at.isnot(None)
    ).order_by(POI.scheduled_at).all()
    
    # Get all POIs without scheduled_at (unscheduled)
    unscheduled_pois = db.query(POI).filter(
        POI.trip_id == trip_id,
        or_(POI.scheduled_at.is_(None), POI.scheduled_at == None)
    ).all()
    
    # Get all ItineraryItems with start_ts
    scheduled_items = db.query(ItineraryItem).filter(
        ItineraryItem.trip_id == trip_id,
        ItineraryItem.start_ts.isnot(None)
    ).order_by(ItineraryItem.start_ts).all()
    
    # Get all ItineraryItems without start_ts (unscheduled)
    unscheduled_items = db.query(ItineraryItem).filter(
        ItineraryItem.trip_id == trip_id,
        or_(ItineraryItem.start_ts.is_(None), ItineraryItem.start_ts == None)
    ).all()
    
    # Combine scheduled activities
    activities = []
    
    # Add POIs as activities
    for poi in scheduled_pois:
        end_time = None
        if poi.scheduled_at and poi.duration_minutes:
            end_time = poi.scheduled_at + timedelta(minutes=poi.duration_minutes)
        
        activity = ScheduleActivity(
            id=f"poi_{poi.id}",
            type="poi",
            name=poi.name,
            start_time=poi.scheduled_at,
            end_time=end_time,
            duration_minutes=poi.duration_minutes,
            poi_id=poi.id,
            address=poi.address,
            city=poi.city,
            country=poi.country,
            estimated_cost=poi.estimated_cost,
            description=poi.notes,
        )
        activities.append(activity)
    
    # Add ItineraryItems as activities
    for item in scheduled_items:
        name = item.name
        if not name and item.poi:
            name = item.poi.name
        elif not name:
            name = "Actividad sin nombre"
        
        activity = ScheduleActivity(
            id=f"item_{item.id}",
            type="itinerary_item",
            name=name,
            start_time=item.start_ts,
            end_time=item.end_ts,
            duration_minutes=int((item.end_ts - item.start_ts).total_seconds() / 60) if item.end_ts and item.start_ts else None,
            itinerary_item_id=item.id,
            poi_id=item.poi_id,
            address=item.poi.address if item.poi else None,
            city=item.poi.city if item.poi else None,
            country=item.poi.country if item.poi else None,
            description=item.poi.notes if item.poi else None,
        )
        activities.append(activity)
    
    # Sort activities by start_time
    activities.sort(key=lambda a: a.start_time or datetime.min)
    
    # Group by day
    days_dict = {}
    for activity in activities:
        if not activity.start_time:
            continue
        
        day_key = activity.start_time.date()
        if day_key not in days_dict:
            days_dict[day_key] = ScheduleDay(date=day_key, activities=[], free_time_slots=[])
        days_dict[day_key].activities.append(activity)
    
    # Detect free time slots for each day
    for day_key, day_schedule in days_dict.items():
        # Sort activities by start_time for this day
        day_schedule.activities.sort(key=lambda a: a.start_time or datetime.min)
        
        # Detect gaps between activities
        for i in range(len(day_schedule.activities) - 1):
            current = day_schedule.activities[i]
            next_activity = day_schedule.activities[i + 1]
            
            if not current.end_time or not next_activity.start_time:
                continue
            
            # If there's a gap of at least 15 minutes, it's free time
            gap_minutes = (next_activity.start_time - current.end_time).total_seconds() / 60
            if gap_minutes >= 15:
                free_time = FreeTimeSlot(
                    start_time=current.end_time,
                    end_time=next_activity.start_time,
                    duration_minutes=int(gap_minutes),
                )
                day_schedule.free_time_slots.append(free_time)
    
    # Convert to list and sort by date
    days_list = sorted(days_dict.values(), key=lambda d: d.date)
    
    # Create response (convert ORM to Pydantic models)
    unscheduled_pois_read = []
    for poi in unscheduled_pois:
        poi_dict = {
            'id': poi.id,
            'trip_id': poi.trip_id,
            'name': poi.name,
            'notes': poi.notes,
            'lat': poi.lat,
            'lng': poi.lng,
            'address': poi.address,
            'city': poi.city,
            'country': poi.country,
            'place_name': poi.place_name,
            'scheduled_at': poi.scheduled_at,
            'duration_minutes': poi.duration_minutes,
            'estimated_cost': poi.estimated_cost,
        }
        unscheduled_pois_read.append(POIRead(**poi_dict))
    
    unscheduled_items_read = []
    for item in unscheduled_items:
        item_dict = {
            'id': item.id,
            'trip_id': item.trip_id,
            'poi_id': item.poi_id,
            'name': item.name,
            'start_ts': item.start_ts,
            'end_ts': item.end_ts,
            'status': item.status,
        }
        unscheduled_items_read.append(ItineraryItemRead(**item_dict))
    
    schedule = TripSchedule(
        trip_id=trip_id,
        days=days_list,
        unscheduled_pois=unscheduled_pois_read,
        unscheduled_items=unscheduled_items_read,
    )
    
    return schedule
