from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='lector',
            options={'verbose_name': 'lector', 'verbose_name_plural': 'lectores'},
        ),
        migrations.AlterModelOptions(
            name='libro',
            options={'verbose_name': 'libro', 'verbose_name_plural': 'libros'},
        ),
        migrations.AlterModelOptions(
            name='prestamo',
            options={'verbose_name': 'préstamo', 'verbose_name_plural': 'préstamos'},
        ),
        migrations.AlterField(
            model_name='libro',
            name='isbn',
            field=models.CharField(max_length=20, unique=True, verbose_name='ISBN'),
        ),
        migrations.AlterField(
            model_name='prestamo',
            name='fecha_devolucion',
            field=models.DateField(blank=True, null=True, verbose_name='fecha de devolución'),
        ),
    ]
