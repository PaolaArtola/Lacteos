from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import timedelta
import random
from lacteos.models import Lacteo, Sale, SaleItem


class Command(BaseCommand):
    help = 'Creates mock sales data for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of mock sales to create (default: 20)',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get or create a user for sales
        user, created = User.objects.get_or_create(
            username='system',
            defaults={'email': 'system@example.com'}
        )
        if created:
            user.set_password('system')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created system user'))
        
        # Get all lacteos
        lacteos = list(Lacteo.objects.all())
        
        if not lacteos:
            self.stdout.write(self.style.ERROR('No lacteos found. Please create some products first.'))
            return
        
        # Customer names for variety
        customer_names = [
            'Juan Pérez', 'María García', 'Carlos López', 'Ana Martínez',
            'Luis Rodríguez', 'Carmen Sánchez', 'Pedro Fernández',
            'Laura Gómez', 'Miguel Torres', 'Sofia Ramírez', 'Diego Morales',
            'Elena Ruiz', 'Roberto Díaz', 'Isabel Jiménez', 'Francisco Moreno',
            'Walk-in Customer', 'Regular Customer', 'Corporate Order'
        ]
        
        # Create mock sales
        created_count = 0
        for i in range(count):
            # Random date within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            sale_date = timezone.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Random customer (or empty for walk-in)
            customer_name = random.choice(customer_names) if random.random() > 0.2 else ''
            
            # Create sale
            sale = Sale.objects.create(
                sale_date=sale_date,
                customer_name=customer_name,
                total_amount=Decimal('0'),
                created_by=user,
                notes=f'Mock sale #{i+1}'
            )
            
            # Add 1-5 items to each sale
            num_items = random.randint(1, 5)
            selected_lacteos = random.sample(lacteos, min(num_items, len(lacteos)))
            
            for lacteo in selected_lacteos:
                quantity = random.randint(1, 10)
                unit_price = lacteo.price
                cost_price = lacteo.cost_price if lacteo.cost_price > 0 else lacteo.price * Decimal('0.6')
                
                SaleItem.objects.create(
                    sale=sale,
                    lacteo=lacteo,
                    quantity=quantity,
                    unit_price=unit_price,
                    cost_price=cost_price
                )
            
            # Recalculate totals
            sale.calculate_totals()
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} mock sales with {SaleItem.objects.filter(sale__in=Sale.objects.filter(created_by=user).order_by('-id')[:count]).count()} items'
            )
        )

