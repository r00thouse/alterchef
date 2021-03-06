
import json
import base64

from django.core import exceptions
from django.db import models
from django.db.models import TextField
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext as _

class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478

    example:
        class Page(models.Model):
            data = JSONField(blank=True, null=True)


        page = Page.objects.get(pk=5)
        page.data = {'title': 'test', 'type': 3}
        page.save()
    """

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)


class PublicKeyField(TextField):
    def validate(self, value, model_instance):
        """
        Confirm that each row is a valid ssh key
        """
        def _validate_key(value):
            """
            Just confirm that the first field is something like ssh-rsa or ssh-dss,
            and the second field is reasonably long and can be base64 decoded.
            """
            if value.strip() == "":
                return True
            try:
                type_, key_string = value.split()[:2]
                assert (type_[:4] == 'ssh-')
                assert (len(key_string) > 100)
                base64.decodestring(key_string)
                return True
            except:
                False

        super(PublicKeyField, self).validate(value, model_instance)
        keys = value.rstrip().split("\n")
        l = len(keys)
        i = 0
        for s in value.split("\n"):
            i += 1
            if not _validate_key(s):
                if l == 1:
                    message = _("This does not appear to be an ssh public key")
                else:
                    message = _("Row %d does not appear"
                                " to be an ssh public key") % i
                raise exceptions.ValidationError(message)

    def clean(self, value, model_instance):
        """
        Clean up any whitespace.
        """
        lines = value.strip().split("\n")
        lines = [" ".join(line.strip().split()) for line in lines]
        value = "\n".join([line for line in lines if line])
        return super(PublicKeyField, self).clean(value, model_instance)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], [".*JSONField"])
add_introspection_rules([], [".*PublicKeyField"])
