# Generated migration for adding summarizer_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0011_add_title_task_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='summarizer_type',
            field=models.CharField(
                choices=[('ollama', 'Ollama (LLM)'), ('bart', 'BART (Hugging Face)')],
                default='ollama',
                help_text='Motor utilizado para generar el resumen del documento',
                max_length=20,
                verbose_name='Tipo de Generador de Resumen'
            ),
        ),
        migrations.AddField(
            model_name='documenttask',
            name='summarizer_type',
            field=models.CharField(
                blank=True,
                choices=[('ollama', 'Ollama (LLM)'), ('bart', 'BART (Hugging Face)')],
                help_text='Motor a utilizar para generar resumen: ollama o bart',
                max_length=20,
                null=True,
                verbose_name='Tipo de Generador de Resumen'
            ),
        ),
    ]
