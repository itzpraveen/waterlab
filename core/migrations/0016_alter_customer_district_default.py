from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_testparameter_name_ci_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='district',
            field=models.CharField(
                choices=[('Thiruvananthapuram', 'Thiruvananthapuram'), ('Kollam', 'Kollam'), ('Pathanamthitta', 'Pathanamthitta'), ('Alappuzha', 'Alappuzha'), ('Kottayam', 'Kottayam'), ('Idukki', 'Idukki'), ('Ernakulam', 'Ernakulam'), ('Thrissur', 'Thrissur'), ('Palakkad', 'Palakkad'), ('Malappuram', 'Malappuram'), ('Kozhikode', 'Kozhikode'), ('Wayanad', 'Wayanad'), ('Kannur', 'Kannur'), ('Kasaragod', 'Kasaragod')],
                default='Thiruvananthapuram',
                max_length=50,
                verbose_name='District',
            ),
        ),
    ]

