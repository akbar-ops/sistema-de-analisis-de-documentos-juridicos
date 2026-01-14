# Generated manually to preserve data when renaming Person fields
from django.db import migrations, models


def copy_normalized_to_name(apps, schema_editor):
    """Copy data from normalized_name to name before removing old fields"""
    Person = apps.get_model('documents', 'Person')
    for person in Person.objects.all():
        # Use normalized_name as the source (already uppercase without accents)
        person.name = person.normalized_name
        person.save(update_fields=['name'])


def reverse_copy(apps, schema_editor):
    """Reverse: copy data from name back to normalized_name"""
    Person = apps.get_model('documents', 'Person')
    for person in Person.objects.all():
        person.normalized_name = person.name
        person.full_name = person.name  # Best effort restoration
        person.save(update_fields=['normalized_name', 'full_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_document_case_number'),
    ]

    operations = [
        # Step 1: Add new 'name' field (nullable at first to allow data migration)
        migrations.AddField(
            model_name='person',
            name='name',
            field=models.CharField(
                max_length=255, 
                db_index=True,
                verbose_name="Nombre",
                help_text="Nombre de persona o entidad en mayúsculas sin tildes",
                null=True,  # Temporarily nullable
                blank=True
            ),
        ),
        
        # Step 2: Copy data from normalized_name to name
        migrations.RunPython(copy_normalized_to_name, reverse_copy),
        
        # Step 3: Make 'name' non-nullable now that data is copied
        migrations.AlterField(
            model_name='person',
            name='name',
            field=models.CharField(
                max_length=255, 
                db_index=True,
                verbose_name="Nombre",
                help_text="Nombre de persona o entidad en mayúsculas sin tildes"
            ),
        ),
        
        # Step 4: Remove old index on normalized_name
        migrations.RemoveIndex(
            model_name='person',
            name='documents_p_normali_8fa582_idx',
        ),
        
        # Step 5: Remove old fields
        migrations.RemoveField(
            model_name='person',
            name='full_name',
        ),
        migrations.RemoveField(
            model_name='person',
            name='normalized_name',
        ),
        
        # Step 6: Update Meta options
        migrations.AlterModelOptions(
            name='person',
            options={
                'ordering': ['name'], 
                'verbose_name': 'Persona/Entidad', 
                'verbose_name_plural': 'Personas/Entidades'
            },
        ),
        migrations.AlterModelOptions(
            name='documentperson',
            options={
                'ordering': ['-is_primary', 'role', 'person__name'], 
                'verbose_name': 'Persona en Documento', 
                'verbose_name_plural': 'Personas en Documentos'
            },
        ),
        
        # Step 7: Add new index on 'name'
        migrations.AddIndex(
            model_name='person',
            index=models.Index(fields=['name'], name='documents_p_name_8cbd08_idx'),
        ),
    ]
