"""
Transfer Verification Protocol API Router
Endpoints for creating, tracking, and verifying medicine transfers
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.db.database import get_session
from app.db.models import Transfer, TransferItem, District, Medicine
from app.services.verification import verification_service

router = APIRouter()


# --- REQUEST/RESPONSE MODELS ---

class TransferItemCreate(BaseModel):
    batch_id: str
    quantity: int
    expiry_date: Optional[str] = None


class TransferCreate(BaseModel):
    medicine_id: str
    quantity: int
    from_district_id: str
    to_district_id: str
    priority: str = "normal"
    created_by: str
    sender_notes: Optional[str] = None
    items: List[TransferItemCreate] = []


class PickupRequest(BaseModel):
    transporter_id: str
    pickup_location_lat: Optional[float] = None
    pickup_location_lng: Optional[float] = None


class DeliveryRequest(BaseModel):
    receiver_id: str
    received_quantity: int
    delivery_location_lat: Optional[float] = None
    delivery_location_lng: Optional[float] = None
    receiver_notes: Optional[str] = None
    item_conditions: Optional[List[dict]] = None  # [{qr_code, condition}]


# --- HELPER FUNCTIONS ---

def get_transfer_dict(transfer: Transfer, items: List[TransferItem] = None) -> dict:
    """Convert Transfer model to dict with computed fields"""
    result = {
        "id": transfer.id,
        "medicine_id": transfer.medicine_id,
        "quantity": transfer.quantity,
        "from_district_id": transfer.from_district_id,
        "to_district_id": transfer.to_district_id,
        "status": transfer.status,
        "priority": transfer.priority,
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
        "created_by": transfer.created_by,
        "sender_signature": transfer.sender_signature,
        "sender_notes": transfer.sender_notes,
        "pickup_at": transfer.pickup_at.isoformat() if transfer.pickup_at else None,
        "transporter_id": transfer.transporter_id,
        "transporter_signature": transfer.transporter_signature,
        "delivered_at": transfer.delivered_at.isoformat() if transfer.delivered_at else None,
        "receiver_id": transfer.receiver_id,
        "receiver_signature": transfer.receiver_signature,
        "received_quantity": transfer.received_quantity,
        "receiver_notes": transfer.receiver_notes,
        "verification_hash": transfer.verification_hash,
        "is_verified": transfer.is_verified,
        "has_discrepancy": transfer.has_discrepancy,
        "discrepancy_type": transfer.discrepancy_type,
        "discrepancy_notes": transfer.discrepancy_notes,
    }
    
    if items:
        result["items"] = [
            {
                "id": item.id,
                "batch_qr_code": item.batch_qr_code,
                "batch_id": item.batch_id,
                "quantity": item.quantity,
                "scanned_at_sender": item.scanned_at_sender,
                "scanned_at_receiver": item.scanned_at_receiver,
                "condition_on_receipt": item.condition_on_receipt
            }
            for item in items
        ]
    
    return result


# --- ENDPOINTS ---

@router.get("/")
async def list_transfers(
    status: Optional[str] = None,
    from_district: Optional[str] = None,
    to_district: Optional[str] = None,
    has_discrepancy: Optional[bool] = None,
    limit: int = Query(50, le=100),
    session: Session = Depends(get_session)
):
    """List all transfers with optional filters"""
    query = select(Transfer).order_by(Transfer.created_at.desc())
    
    if status:
        query = query.where(Transfer.status == status)
    if from_district:
        query = query.where(Transfer.from_district_id == from_district)
    if to_district:
        query = query.where(Transfer.to_district_id == to_district)
    if has_discrepancy is not None:
        query = query.where(Transfer.has_discrepancy == has_discrepancy)
    
    query = query.limit(limit)
    transfers = session.exec(query).all()
    
    # Get summary stats
    total_query = select(Transfer)
    all_transfers = session.exec(total_query).all()
    
    status_counts = {}
    for t in all_transfers:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
    
    discrepancy_count = len([t for t in all_transfers if t.has_discrepancy])
    
    return {
        "transfers": [get_transfer_dict(t) for t in transfers],
        "count": len(transfers),
        "summary": {
            "by_status": status_counts,
            "with_discrepancies": discrepancy_count
        }
    }


@router.post("/")
async def create_transfer(
    data: TransferCreate,
    session: Session = Depends(get_session)
):
    """
    Step 1: Sender creates a new transfer.
    Generates transfer ID and sender signature.
    """
    # Validate districts
    from_district = session.get(District, data.from_district_id)
    to_district = session.get(District, data.to_district_id)
    
    if not from_district:
        raise HTTPException(404, f"Source district {data.from_district_id} not found")
    if not to_district:
        raise HTTPException(404, f"Destination district {data.to_district_id} not found")
    if data.from_district_id == data.to_district_id:
        raise HTTPException(400, "Source and destination districts must be different")
    
    # Validate medicine
    medicine = session.get(Medicine, data.medicine_id)
    if not medicine:
        raise HTTPException(404, f"Medicine {data.medicine_id} not found")
    
    # Generate transfer ID
    transfer_id = verification_service.generate_transfer_id()
    
    # Create transfer items with QR codes
    items_for_signature = []
    transfer_items = []
    
    for item_data in data.items:
        qr_code = verification_service.generate_batch_qr(
            data.medicine_id,
            item_data.batch_id,
            item_data.quantity
        )
        items_for_signature.append({"qr": qr_code, "qty": item_data.quantity})
        
        transfer_item = TransferItem(
            transfer_id=transfer_id,
            batch_qr_code=qr_code,
            batch_id=item_data.batch_id,
            quantity=item_data.quantity,
            scanned_at_sender=True,
            sender_scan_time=datetime.now()
        )
        transfer_items.append(transfer_item)
    
    # If no items provided, create a single default item
    if not transfer_items:
        qr_code = verification_service.generate_batch_qr(
            data.medicine_id,
            f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            data.quantity
        )
        items_for_signature.append({"qr": qr_code, "qty": data.quantity})
        
        transfer_item = TransferItem(
            transfer_id=transfer_id,
            batch_qr_code=qr_code,
            batch_id=f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            quantity=data.quantity,
            scanned_at_sender=True,
            sender_scan_time=datetime.now()
        )
        transfer_items.append(transfer_item)
    
    # Create sender signature
    sender_signature = verification_service.create_signature(
        party_id=data.created_by,
        transfer_id=transfer_id,
        items=items_for_signature,
        timestamp=datetime.now()
    )
    
    # Create transfer record
    transfer = Transfer(
        id=transfer_id,
        medicine_id=data.medicine_id,
        quantity=data.quantity,
        from_district_id=data.from_district_id,
        to_district_id=data.to_district_id,
        priority=data.priority,
        created_by=data.created_by,
        sender_signature=sender_signature,
        sender_notes=data.sender_notes,
        status="created"
    )
    
    session.add(transfer)
    for item in transfer_items:
        session.add(item)
    session.commit()
    session.refresh(transfer)
    
    return {
        "message": "Transfer created successfully",
        "transfer": get_transfer_dict(transfer, transfer_items),
        "sender_signature": sender_signature,
        "qr_codes": [item.batch_qr_code for item in transfer_items]
    }


@router.get("/{transfer_id}")
async def get_transfer(
    transfer_id: str,
    session: Session = Depends(get_session)
):
    """Get detailed transfer information"""
    transfer = session.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(404, f"Transfer {transfer_id} not found")
    
    items = session.exec(
        select(TransferItem).where(TransferItem.transfer_id == transfer_id)
    ).all()
    
    # Run verification
    transfer_dict = get_transfer_dict(transfer, items)
    items_dict = [{"scanned_at_sender": i.scanned_at_sender, "scanned_at_receiver": i.scanned_at_receiver} for i in items]
    
    verification = verification_service.verify_transfer(transfer_dict, items_dict)
    
    return {
        "transfer": transfer_dict,
        "verification": {
            "is_valid": verification.is_valid,
            "chain_complete": verification.chain_complete,
            "signatures": verification.signatures,
            "anomalies": verification.anomalies,
            "verification_hash": verification.verification_hash
        }
    }


@router.post("/{transfer_id}/pickup")
async def record_pickup(
    transfer_id: str,
    data: PickupRequest,
    session: Session = Depends(get_session)
):
    """
    Step 2: Transporter acknowledges pickup.
    Records pickup time, location, and creates transporter signature.
    """
    transfer = session.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(404, f"Transfer {transfer_id} not found")
    
    if transfer.status != "created":
        raise HTTPException(400, f"Transfer is in '{transfer.status}' status, cannot pickup")
    
    # Get items for signature
    items = session.exec(
        select(TransferItem).where(TransferItem.transfer_id == transfer_id)
    ).all()
    items_for_signature = [{"qr": i.batch_qr_code, "qty": i.quantity} for i in items]
    
    # Create transporter signature
    pickup_time = datetime.now()
    transporter_signature = verification_service.create_signature(
        party_id=data.transporter_id,
        transfer_id=transfer_id,
        items=items_for_signature,
        timestamp=pickup_time
    )
    
    # Update transfer
    transfer.status = "picked_up"
    transfer.pickup_at = pickup_time
    transfer.transporter_id = data.transporter_id
    transfer.transporter_signature = transporter_signature
    transfer.pickup_location_lat = data.pickup_location_lat
    transfer.pickup_location_lng = data.pickup_location_lng
    
    # Estimate delivery time (simple calculation)
    transfer.expected_delivery_at = pickup_time + timedelta(hours=verification_service.MAX_TRANSIT_HOURS)
    
    session.commit()
    session.refresh(transfer)
    
    return {
        "message": "Pickup recorded successfully",
        "transfer": get_transfer_dict(transfer),
        "transporter_signature": transporter_signature
    }


@router.post("/{transfer_id}/deliver")
async def record_delivery(
    transfer_id: str,
    data: DeliveryRequest,
    session: Session = Depends(get_session)
):
    """
    Step 3: Receiver confirms delivery.
    Verifies quantities, creates receiver signature, and runs integrity check.
    """
    transfer = session.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(404, f"Transfer {transfer_id} not found")
    
    if transfer.status != "picked_up":
        raise HTTPException(400, f"Transfer is in '{transfer.status}' status, cannot deliver")
    
    # Get items
    items = session.exec(
        select(TransferItem).where(TransferItem.transfer_id == transfer_id)
    ).all()
    items_for_signature = [{"qr": i.batch_qr_code, "qty": i.quantity} for i in items]
    
    # Update item scanning status
    for item in items:
        item.scanned_at_receiver = True
        item.receiver_scan_time = datetime.now()
        
        # Update condition if provided
        if data.item_conditions:
            for cond in data.item_conditions:
                if cond.get("qr_code") == item.batch_qr_code:
                    item.condition_on_receipt = cond.get("condition", "good")
    
    # Create receiver signature
    delivery_time = datetime.now()
    receiver_signature = verification_service.create_signature(
        party_id=data.receiver_id,
        transfer_id=transfer_id,
        items=items_for_signature,
        timestamp=delivery_time
    )
    
    # Update transfer
    transfer.status = "delivered"
    transfer.delivered_at = delivery_time
    transfer.receiver_id = data.receiver_id
    transfer.receiver_signature = receiver_signature
    transfer.received_quantity = data.received_quantity
    transfer.receiver_notes = data.receiver_notes
    transfer.delivery_location_lat = data.delivery_location_lat
    transfer.delivery_location_lng = data.delivery_location_lng
    
    # Run verification
    transfer_dict = get_transfer_dict(transfer)
    items_dict = [{"scanned_at_sender": i.scanned_at_sender, "scanned_at_receiver": i.scanned_at_receiver} for i in items]
    
    verification = verification_service.verify_transfer(transfer_dict, items_dict)
    
    # Update verification status
    transfer.verification_hash = verification.verification_hash
    transfer.is_verified = verification.is_valid
    transfer.verified_at = datetime.now() if verification.is_valid else None
    
    # Check for discrepancies
    if verification.anomalies:
        critical_anomalies = [a for a in verification.anomalies if a["severity"] == "critical"]
        if critical_anomalies:
            transfer.has_discrepancy = True
            transfer.discrepancy_type = critical_anomalies[0]["type"]
            transfer.discrepancy_notes = "; ".join([a["message"] for a in critical_anomalies])
            transfer.status = "disputed"
        else:
            transfer.status = "verified"
    else:
        transfer.status = "verified"
    
    session.commit()
    session.refresh(transfer)
    
    return {
        "message": "Delivery recorded successfully",
        "transfer": get_transfer_dict(transfer, items),
        "verification": {
            "is_valid": verification.is_valid,
            "chain_complete": verification.chain_complete,
            "verification_hash": verification.verification_hash,
            "anomalies": verification.anomalies
        }
    }


@router.get("/{transfer_id}/verify")
async def verify_transfer(
    transfer_id: str,
    session: Session = Depends(get_session)
):
    """Verify the integrity of a transfer's chain of custody"""
    transfer = session.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(404, f"Transfer {transfer_id} not found")
    
    items = session.exec(
        select(TransferItem).where(TransferItem.transfer_id == transfer_id)
    ).all()
    
    transfer_dict = get_transfer_dict(transfer)
    items_dict = [{"scanned_at_sender": i.scanned_at_sender, "scanned_at_receiver": i.scanned_at_receiver} for i in items]
    
    verification = verification_service.verify_transfer(transfer_dict, items_dict)
    
    return {
        "transfer_id": transfer_id,
        "is_valid": verification.is_valid,
        "chain_complete": verification.chain_complete,
        "signatures": verification.signatures,
        "verification_hash": verification.verification_hash,
        "anomalies": verification.anomalies,
        "status": transfer.status
    }


@router.get("/pending/list")
async def get_pending_transfers(
    session: Session = Depends(get_session)
):
    """Get transfers requiring action (not yet verified)"""
    query = select(Transfer).where(
        Transfer.status.in_(["created", "picked_up"])
    ).order_by(Transfer.created_at)
    
    transfers = session.exec(query).all()
    
    # Check for anomalies
    transfer_dicts = [get_transfer_dict(t) for t in transfers]
    alerts = verification_service.detect_pending_anomalies(transfer_dicts)
    
    return {
        "pending_transfers": transfer_dicts,
        "count": len(transfers),
        "alerts": alerts,
        "alert_count": len(alerts)
    }


@router.get("/anomalies/list")
async def get_anomalous_transfers(
    session: Session = Depends(get_session)
):
    """Get all transfers with discrepancies or anomalies"""
    query = select(Transfer).where(
        Transfer.has_discrepancy == True
    ).order_by(Transfer.created_at.desc())
    
    transfers = session.exec(query).all()
    
    results = []
    for transfer in transfers:
        items = session.exec(
            select(TransferItem).where(TransferItem.transfer_id == transfer.id)
        ).all()
        
        transfer_dict = get_transfer_dict(transfer, items)
        items_dict = [{"scanned_at_sender": i.scanned_at_sender, "scanned_at_receiver": i.scanned_at_receiver} for i in items]
        
        verification = verification_service.verify_transfer(transfer_dict, items_dict)
        
        results.append({
            "transfer": transfer_dict,
            "anomalies": verification.anomalies
        })
    
    return {
        "anomalous_transfers": results,
        "count": len(results)
    }
