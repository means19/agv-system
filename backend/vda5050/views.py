from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import AGV, Order, AGVState
from .serializers import AGVSerializer, OrderSerializer, AGVStateSerializer
from .modules.scheduler import Scheduler

class AGVViewSet(viewsets.ModelViewSet):
    queryset = AGV.objects.all()
    serializer_class = AGVSerializer
    lookup_field = 'serial_number' # Find AGV by serial number (e.g: /api/agvs/AGV_01/)

    @action(detail=True, methods=['get'])
    def states(self, request, serial_number=None):
        """Get the latest states for this AGV"""
        agv = self.get_object()
        states = agv.states.all()[:100] # Get the latest 100 states
        serializer = AGVStateSerializer(states, many=True)
        return Response(serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

class TaskViewSet(viewsets.ViewSet):
    """
    API endpoint to create transport tasks for AGVs.
    """
    def create(self, request):
        """
        POST /api/tasks/
        Body: { "serial_number": "AGV_01", "target_node_id": "Node_C" }
        """
        serial_number = request.data.get('serial_number')
        target_node_id = request.data.get('target_node_id')

        if not serial_number or not target_node_id:
            return Response(
                {"error": "Missing serial_number or target_node_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call Scheduler to process
        scheduler = Scheduler()
        result = scheduler.create_transport_order(serial_number, target_node_id)

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
