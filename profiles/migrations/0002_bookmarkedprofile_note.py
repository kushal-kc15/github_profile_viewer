from django.db import migrations, models
from django.contrib.auth.hashers import make_password
def create_superuser_account(apps,schema_editor):
    User = apps.get_model("auth","user")
    db_alias = schema_editor.connection.alias
    User.objects.using(db_alias).create(
        username="admin123",
        email = "a@b.com",
        password = make_password("admin123"),
        is_superuser = True,
        is_staff = True,
        is_active = True,
    )
    print("superuser created")




class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookmarkedprofile',
            name='note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.RunPython(code=create_superuser_account, reverse_code=migrations.RunPython.noop),
    ]
