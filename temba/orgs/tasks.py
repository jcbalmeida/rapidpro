from datetime import timedelta

from smartmin.csv_imports.models import ImportTask

from django.utils import timezone

from celery.task import task

from temba.contacts.models import ExportContactsTask
from temba.contacts.tasks import export_contacts_task
from temba.flows.models import ExportFlowResultsTask
from temba.flows.tasks import export_flow_results_task
from temba.msgs.models import ExportMessagesTask
from temba.msgs.tasks import export_messages_task
from temba.utils.celery import nonoverlapping_task

from .models import CreditAlert, Invitation, Org, TopUpCredits


@task(track_started=True, name="send_invitation_email_task")
def send_invitation_email_task(invitation_id):
    invitation = Invitation.objects.get(pk=invitation_id)
    invitation.send_email()


@task(track_started=True, name="send_alert_email_task")
def send_alert_email_task(alert_id):
    alert = CreditAlert.objects.get(pk=alert_id)
    alert.send_email()


@task(track_started=True, name="check_credits_task")
def check_credits_task():  # pragma: needs cover
    CreditAlert.check_org_credits()


@task(track_started=True, name="check_topup_expiration_task")
def check_topup_expiration_task():
    CreditAlert.check_topup_expiration()


@task(track_started=True, name="apply_topups_task")
def apply_topups_task(org_id):
    org = Org.objects.get(id=org_id)
    org.apply_topups()
    org.trigger_send()


@nonoverlapping_task(track_started=True, name="squash_topupcredits", lock_key="squash_topupcredits", lock_timeout=7200)
def squash_topupcredits():
    TopUpCredits.squash()


@nonoverlapping_task(track_started=True, name="resume_failed_tasks", lock_key="resume_failed_tasks", lock_timeout=7200)
def resume_failed_tasks():
    now = timezone.now()
    window = now - timedelta(hours=1)
    oldest_retry_time = now - timedelta(days=2)
    permanent_failed_time = now - timedelta(days=5)

    import_tasks = list(ImportTask.objects.filter(modified_on__lte=window, created_on__gte=oldest_retry_time).exclude(
        task_status__in=[ImportTask.SUCCESS, ImportTask.FAILURE]
    ))
    for import_task in import_tasks:
        import_task.start()

    ImportTask.objects.filter(pk__in=[elt.id for elt in import_tasks]).update(modified_on=now)

    ImportTask.objects.filter(created_on__lt=permanent_failed_time).exclude(
        task_status__in=[ImportTask.SUCCESS, ImportTask.FAILURE]
    ).update(task_status=ImportTask.FAILURE)

    contact_exports = list(ExportContactsTask.objects.filter(
        modified_on__lte=window, created_on__gte=oldest_retry_time
    ).exclude(status__in=[ExportContactsTask.STATUS_COMPLETE, ExportContactsTask.STATUS_FAILED]))
    for contact_export in contact_exports:
        export_contacts_task.delay(contact_export.pk)

    ExportContactsTask.objects.filter(pk__in=[elt.id for elt in contact_exports]).update(modified_on=now)

    ExportContactsTask.objects.filter(created_on__lt=permanent_failed_time).exclude(
        status__in=[ExportContactsTask.STATUS_COMPLETE, ExportContactsTask.STATUS_FAILED]
    ).update(status=ExportContactsTask.STATUS_FAILED)

    flow_results_exports = list(ExportFlowResultsTask.objects.filter(
        modified_on__lte=window, created_on__gte=oldest_retry_time
    ).exclude(status__in=[ExportFlowResultsTask.STATUS_COMPLETE, ExportFlowResultsTask.STATUS_FAILED]))
    for flow_results_export in flow_results_exports:
        export_flow_results_task.delay(flow_results_export.pk)

    ExportFlowResultsTask.objects.filter(pk__in=[elt.id for elt in flow_results_exports]).update(modified_on=now)

    ExportFlowResultsTask.objects.filter(created_on__lt=permanent_failed_time).exclude(
        status__in=[ExportFlowResultsTask.STATUS_COMPLETE, ExportFlowResultsTask.STATUS_FAILED]
    ).update(status=ExportFlowResultsTask.STATUS_FAILED)

    msg_exports = list(ExportMessagesTask.objects.filter(
        modified_on__lte=window, created_on__gte=oldest_retry_time
    ).exclude(status__in=[ExportMessagesTask.STATUS_COMPLETE, ExportMessagesTask.STATUS_FAILED]))
    for msg_export in msg_exports:
        export_messages_task.delay(msg_export.pk)

    ExportMessagesTask.objects.filter(pk__in=[elt.id for elt in msg_exports]).update(modified_on=now)

    ExportMessagesTask.objects.filter(created_on__lt=permanent_failed_time).exclude(
        status__in=[ExportMessagesTask.STATUS_COMPLETE, ExportMessagesTask.STATUS_FAILED]
    ).update(status=ExportMessagesTask.STATUS_FAILED)
