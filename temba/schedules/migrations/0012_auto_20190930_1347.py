# Generated by Django 2.2.4 on 2019-09-30 13:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("schedules", "0011_populate_org")]

    operations = [
        migrations.RemoveField(model_name="schedule", name="repeat_days"),
        migrations.RemoveField(model_name="schedule", name="status"),
        migrations.AlterField(
            model_name="schedule",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="schedules", to="orgs.Org"
            ),
        ),
    ]