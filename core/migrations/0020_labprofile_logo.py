from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_labprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='labprofile',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='lab_brands/'),
        ),
    ]
