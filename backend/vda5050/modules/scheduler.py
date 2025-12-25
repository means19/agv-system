import uuid
from django.utils import timezone
from vda5050.models import AGV, AGVState, Order
from vda5050.graph_engine import GraphEngine

class Scheduler:
    def __init__(self):
        self.graph_engine = GraphEngine()

    def create_transport_order(self, serial_number, target_node_id):
        """
        Create transport order for AGV to move to the target node.
        """
        # 1. Get AGV info and current position
        try:
            agv = AGV.objects.get(serial_number=serial_number)
            # Get the latest state to know where the AGV is
            last_state = AGVState.objects.filter(agv=agv).order_by('-timestamp').first()
            
            if not last_state:
                return {"success": False, "error": "AGV has no position data (State)"}
            
            start_node_id = last_state.last_node_id
            
            # If the AGV is already at the target, do nothing
            if start_node_id == target_node_id:
                return {"success": False, "error": "AGV is already at the target node"}

        except AGV.DoesNotExist:
            return {"success": False, "error": "AGV does not exist"}

        # 2. Xác định điểm xuất phát (Start Node)
        # Tìm xem có lệnh nào đang chạy hoặc đang chờ không?
        last_active_order = Order.objects.filter(
            agv=agv, 
            status__in=['SENT', 'ACTIVE', 'QUEUED']
        ).order_by('-created_at').first()

        if last_active_order:
            # --- LOGIC MỚI: NỐI ĐUÔI ---
            # Nếu xe đang bận, điểm xuất phát là điểm cuối của lệnh trước đó
            try:
                start_node_id = last_active_order.nodes[-1]['nodeId']
                initial_status = 'QUEUED'
                print(f"Chaining order: Start from {start_node_id} (End of Order {last_active_order.order_id})")
            except (IndexError, KeyError, TypeError):
                # Fallback nếu dữ liệu lệnh cũ bị lỗi
                return {"success": False, "error": "Lỗi dữ liệu Nodes của lệnh trước đó"}
        else:
            # Nếu xe rảnh, lấy vị trí hiện tại từ State
            last_state = AGVState.objects.filter(agv=agv).order_by('-timestamp').first()
            if not last_state:
                return {"success": False, "error": "AGV chưa có dữ liệu vị trí (State)"}
            
            start_node_id = last_state.last_node_id
            initial_status = 'CREATED' # Sẽ được gửi đi ngay

        # Nếu điểm xuất phát trùng đích đến
        if start_node_id == target_node_id:
            return {"success": False, "error": f"AGV đã ở (hoặc sẽ đến) {target_node_id}"}
        
        # 3. Calculate path (Baseline Calculation)
        nodes, edges = self.graph_engine.get_path(start_node_id, target_node_id)
        
        if not nodes:
            return {"success": False, "error": f"Path not found from {start_node_id} to {target_node_id}"}

        # 5. Create new Order in Database
        # (Signal post_save will automatically send MQTT)
        new_order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
        
        order = Order.objects.create(
            header_id=0,
            timestamp=timezone.now(),
            order_id=new_order_id,
            order_update_id=0,
            zone_set_id="zone_1",
            agv=agv,
            status=initial_status,
            nodes=nodes, # JSON từ GraphEngine
            edges=edges  # JSON từ GraphEngine
        )

        msg = "Order sent to AGV" if initial_status == 'CREATED' else f"Order added to Queue (Start from {start_node_id})"
        
        return {
            "success": True, 
            "order_id": new_order_id, 
            "status": initial_status,
            "message": msg,
            "path": [n['nodeId'] for n in nodes]
        }