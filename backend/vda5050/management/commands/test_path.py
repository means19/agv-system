from django.core.management.base import BaseCommand
from vda5050.graph_engine import GraphEngine
import json

class Command(BaseCommand):
    help = 'Test tìm đường đi ngắn nhất'

    def add_arguments(self, parser):
        parser.add_argument('start', type=str)
        parser.add_argument('end', type=str)

    def handle(self, *args, **kwargs):
        start = kwargs['start']
        end = kwargs['end']
        
        self.stdout.write(f"🔍 Đang tìm đường từ {start} -> {end}...")
        
        engine = GraphEngine()
        nodes, edges = engine.get_path(start, end)
        
        if nodes:
            self.stdout.write(self.style.SUCCESS(f"✅ Tìm thấy lộ trình!"))
            self.stdout.write(f"👉 Đi qua: {[n['nodeId'] for n in nodes]}")
            self.stdout.write(f"👉 Tổng số bước: {len(nodes)} nodes, {len(edges)} edges")
            # In thử JSON ra xem
            # self.stdout.write(json.dumps(nodes, indent=2))
        else:
            self.stdout.write(self.style.ERROR("❌ Không tìm thấy đường đi (Kiểm tra lại tên Node hoặc Map)"))