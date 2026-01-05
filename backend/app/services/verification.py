"""
Transfer Verification Service
Cryptographic chain of custody for anti-corruption medicine transfers
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result of transfer verification"""
    is_valid: bool
    verification_hash: str
    anomalies: List[Dict]
    chain_complete: bool
    signatures: Dict[str, bool]


class TransferVerificationService:
    """
    Provides cryptographic verification for medicine transfers.
    Implements SHA256 hashing and multi-party signature verification.
    """
    
    # Time limits for anomaly detection
    MAX_TRANSIT_HOURS = 48  # Maximum expected transit time
    PICKUP_DEADLINE_HOURS = 24  # Transporter must pickup within 24 hours
    
    @staticmethod
    def generate_transfer_id() -> str:
        """Generate unique transfer ID"""
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"
    
    @staticmethod
    def generate_batch_qr(medicine_id: str, batch_id: str, quantity: int) -> str:
        """Generate unique QR code for a medicine batch"""
        data = f"{medicine_id}:{batch_id}:{quantity}:{datetime.now().isoformat()}"
        return f"QR-{hashlib.sha256(data.encode()).hexdigest()[:16].upper()}"
    
    @staticmethod
    def create_signature(
        party_id: str,
        transfer_id: str,
        items: List[Dict],
        timestamp: datetime,
        photo_hash: Optional[str] = None
    ) -> str:
        """
        Create SHA256 signature for a party's action.
        This signature proves what was sent/received at a specific time.
        """
        # Normalize items for consistent hashing
        normalized_items = sorted(
            [{"qr": item["qr"], "qty": item["qty"]} for item in items],
            key=lambda x: x["qr"]
        )
        
        payload = {
            "party_id": party_id,
            "transfer_id": transfer_id,
            "items": normalized_items,
            "timestamp": timestamp.isoformat(),
            "photo_hash": photo_hash
        }
        
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    @staticmethod
    def hash_photo(photo_data: bytes) -> str:
        """Create hash of photo evidence"""
        return hashlib.sha256(photo_data).hexdigest()
    
    @staticmethod
    def create_verification_hash(
        sender_signature: str,
        transporter_signature: str,
        receiver_signature: str
    ) -> str:
        """
        Create final verification hash combining all 3 signatures.
        This proves the complete chain of custody is intact.
        """
        combined = f"{sender_signature}:{transporter_signature}:{receiver_signature}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_transfer(
        self,
        transfer: Dict,
        items: List[Dict]
    ) -> VerificationResult:
        """
        Comprehensive verification of a transfer.
        Checks signatures, timing, quantities, and detects anomalies.
        """
        anomalies = []
        signatures = {
            "sender": bool(transfer.get("sender_signature")),
            "transporter": bool(transfer.get("transporter_signature")),
            "receiver": bool(transfer.get("receiver_signature"))
        }
        
        # Check 1: All signatures present
        chain_complete = all(signatures.values())
        if not chain_complete:
            missing = [k for k, v in signatures.items() if not v]
            anomalies.append({
                "type": "signature_missing",
                "severity": "critical",
                "message": f"Missing signatures from: {', '.join(missing)}"
            })
        
        # Check 2: Quantity mismatch
        sent_quantity = transfer.get("quantity", 0)
        received_quantity = transfer.get("received_quantity")
        if received_quantity is not None and received_quantity != sent_quantity:
            discrepancy = sent_quantity - received_quantity
            anomalies.append({
                "type": "quantity_mismatch",
                "severity": "critical",
                "message": f"Quantity discrepancy: Sent {sent_quantity}, Received {received_quantity} (Missing: {discrepancy})",
                "missing_units": discrepancy
            })
        
        # Check 3: Item-level verification
        if items:
            unscanned_sender = [i for i in items if not i.get("scanned_at_sender")]
            unscanned_receiver = [i for i in items if not i.get("scanned_at_receiver")]
            
            if unscanned_sender:
                anomalies.append({
                    "type": "incomplete_sender_scan",
                    "severity": "warning",
                    "message": f"{len(unscanned_sender)} items not scanned by sender"
                })
            
            if unscanned_receiver:
                anomalies.append({
                    "type": "incomplete_receiver_scan",
                    "severity": "warning",
                    "message": f"{len(unscanned_receiver)} items not scanned by receiver"
                })
        
        # Check 4: Time violations
        created_at = transfer.get("created_at")
        pickup_at = transfer.get("pickup_at")
        delivered_at = transfer.get("delivered_at")
        
        if created_at and pickup_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            if isinstance(pickup_at, str):
                pickup_at = datetime.fromisoformat(pickup_at)
            
            pickup_delay = (pickup_at - created_at).total_seconds() / 3600
            if pickup_delay > self.PICKUP_DEADLINE_HOURS:
                anomalies.append({
                    "type": "late_pickup",
                    "severity": "warning",
                    "message": f"Pickup delayed by {pickup_delay:.1f} hours (expected: {self.PICKUP_DEADLINE_HOURS}h)"
                })
        
        if pickup_at and delivered_at:
            if isinstance(pickup_at, str):
                pickup_at = datetime.fromisoformat(pickup_at)
            if isinstance(delivered_at, str):
                delivered_at = datetime.fromisoformat(delivered_at)
            
            transit_time = (delivered_at - pickup_at).total_seconds() / 3600
            if transit_time > self.MAX_TRANSIT_HOURS:
                anomalies.append({
                    "type": "extended_transit",
                    "severity": "warning",
                    "message": f"Transit took {transit_time:.1f} hours (expected max: {self.MAX_TRANSIT_HOURS}h)"
                })
        
        # Generate verification hash if chain is complete
        verification_hash = ""
        if chain_complete:
            verification_hash = self.create_verification_hash(
                transfer.get("sender_signature", ""),
                transfer.get("transporter_signature", ""),
                transfer.get("receiver_signature", "")
            )
        
        # Determine validity
        is_valid = chain_complete and not any(
            a["severity"] == "critical" for a in anomalies
        )
        
        return VerificationResult(
            is_valid=is_valid,
            verification_hash=verification_hash,
            anomalies=anomalies,
            chain_complete=chain_complete,
            signatures=signatures
        )
    
    def detect_pending_anomalies(
        self,
        transfers: List[Dict]
    ) -> List[Dict]:
        """
        Scan all transfers for potential issues.
        Called periodically to catch stalled or suspicious transfers.
        """
        alerts = []
        now = datetime.now()
        
        for transfer in transfers:
            transfer_id = transfer.get("id")
            status = transfer.get("status")
            created_at = transfer.get("created_at")
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            # Check for stalled transfers
            if status == "created":
                age_hours = (now - created_at).total_seconds() / 3600
                if age_hours > self.PICKUP_DEADLINE_HOURS:
                    alerts.append({
                        "transfer_id": transfer_id,
                        "type": "stalled_transfer",
                        "severity": "warning",
                        "message": f"Transfer awaiting pickup for {age_hours:.1f} hours",
                        "from_district": transfer.get("from_district_id"),
                        "to_district": transfer.get("to_district_id")
                    })
            
            elif status == "picked_up":
                pickup_at = transfer.get("pickup_at")
                if isinstance(pickup_at, str):
                    pickup_at = datetime.fromisoformat(pickup_at)
                
                if pickup_at:
                    transit_hours = (now - pickup_at).total_seconds() / 3600
                    if transit_hours > self.MAX_TRANSIT_HOURS:
                        alerts.append({
                            "transfer_id": transfer_id,
                            "type": "overdue_delivery",
                            "severity": "critical",
                            "message": f"In transit for {transit_hours:.1f} hours - possible diversion",
                            "from_district": transfer.get("from_district_id"),
                            "to_district": transfer.get("to_district_id")
                        })
        
        return alerts


# Singleton instance
verification_service = TransferVerificationService()
