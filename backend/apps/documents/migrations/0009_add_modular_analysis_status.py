# Generated migration for modular analysis status

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_add_enhanced_embedding'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(
                choices=[
                    ('uploaded', 'Subido'), 
                    ('processing', 'Procesando'), 
                    ('processed', 'Procesado'), 
                    ('partial', 'Parcialmente Procesado'),
                    ('failed', 'Falló')
                ],
                default='uploaded',
                max_length=20,
                verbose_name='Estado'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='metadata_analysis_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('processing', 'Procesando'),
                    ('completed', 'Completado'),
                    ('failed', 'Falló')
                ],
                default='pending',
                max_length=20,
                verbose_name='Estado Análisis de Metadatos'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='summary_analysis_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('processing', 'Procesando'),
                    ('completed', 'Completado'),
                    ('failed', 'Falló')
                ],
                default='pending',
                max_length=20,
                verbose_name='Estado Análisis de Resumen'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='persons_analysis_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('processing', 'Procesando'),
                    ('completed', 'Completado'),
                    ('failed', 'Falló')
                ],
                default='pending',
                max_length=20,
                verbose_name='Estado Análisis de Personas'
            ),
        ),
    ]
