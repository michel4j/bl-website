from django import forms
from django.conf import settings
from django.core.mail import send_mail
#from django.core.mail import mail_admins
from django.template import loader
from django.template import RequestContext
from django.contrib.sites.models import Site

from captcha.fields import ReCaptchaField

# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary.
attrs_dict = { 'class': 'required' }

class ApplicationForm(forms.Form):
    choices = ( ('yes','Yes'),
                ('no','No'),)
    xtal_choices = ( ('yes','Yes, I will bring my own crystals.'),
                ('no','No, I will use standard crystals provided at the school.'),)
    stay_choices = ( ('yes','Yes'),
                     ('no','No, I will make my own accommodation arrangements.'),)
    def __init__(self, data=None, files=None, request=None, *args, **kwargs):
        if request is None:
            raise TypeError("Keyword argument 'request' must be supplied")
        super(ApplicationForm, self).__init__(data=data, files=files, *args, **kwargs)
        self.request = request
    
    name = forms.CharField(max_length=100, required=True,
               widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=1)))
    email = forms.EmailField(required=True,
               widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=200, tabindex=2)))
    phone = forms.CharField(max_length=100, required=False,
               widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=3)))
    institution = forms.CharField(max_length=100, 
               widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=4)))
    addr1 = forms.CharField(max_length=100,  label='Street Address',
               widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=5)))
    addr2 = forms.CharField(max_length=100, required=False, label='Address Line 2 (if needed)',
               widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=6)))
    city = forms.CharField(max_length=100,  label='City',
               widget=forms.TextInput(attrs={'class': 'required half', 'tabindex':7}))
    state = forms.CharField(max_length=100,  label='Province / State / Region',
               widget=forms.TextInput(attrs={'class': 'required half', 'tabindex':8}))
    code = forms.CharField(max_length=100,  label='Postal Code / Zip Code',
               widget=forms.TextInput(attrs={'class': 'required half', 'tabindex':9}))
    country = forms.CharField(max_length=100, label='Country',
               widget=forms.TextInput(attrs={'class': 'required half', 'tabindex':10}))

    sup_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=11)), required=False)
    sup_email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=200, tabindex=12)), required=False)
    sup_phone = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=13)), required=False)
    sup_addr1 = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=14)), required=False)
    sup_addr2 = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=15)), required=False)
    sup_city = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=16)), required=False)
    sup_state = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=17)), required=False)
    sup_code = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=18)), required=False)
    sup_country = forms.CharField(max_length=100, widget=forms.TextInput(attrs=dict(attrs_dict, tabindex=19)), required=False)

    undergrad = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=20)), required=False)
    masters = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=21)), required=False)
    phd = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=22)), required=False)
    postdoc = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=23)), required=False)
    faculty = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=24)), required=False)
    staff = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=25)), required=False)
    other = forms.BooleanField(widget=forms.CheckboxInput(attrs=dict(attrs_dict, tabindex=26)), required=False)
    other_text = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'required half', 'tabindex':27, 'style': 'float:none;'}), required=False)

    travel = forms.ChoiceField(choices=choices,widget=forms.RadioSelect, required=False)
    visa = forms.ChoiceField(choices=choices,widget=forms.RadioSelect, required=False)
    stay = forms.ChoiceField(choices=stay_choices,widget=forms.RadioSelect, required=False)

    crystals = forms.ChoiceField(choices=xtal_choices,widget=forms.RadioSelect)

    research = forms.CharField(widget=forms.Textarea(attrs=dict(attrs_dict, tabindex=34)))
    benefit = forms.CharField(widget=forms.Textarea(attrs=dict(attrs_dict, tabindex=35)))
    
    captcha = ReCaptchaField(label=u'',attrs={'theme' : 'clean','tabindex': 36})
    
    from_email = settings.SCHOOL_FROM_EMAIL
    
    recipient_list = [mail_tuple[1] for mail_tuple in settings.MANAGERS]

    subject_template_name = "application_form/application_form_subject.txt"
    
    template_name = 'application_form/application_form.txt'

    def message(self):
        """
        Render the body of the message to a string.
        
        """
        if callable(self.template_name):
            template_name = self.template_name()
        else:
            template_name = self.template_name
        return loader.render_to_string(template_name,
                                       self.get_context())
    
    def subject(self):
        """
        Render the subject of the message to a string.
        
        """
        subject = loader.render_to_string(self.subject_template_name,
                                          self.get_context())
        return ''.join(subject.splitlines())
    
    def get_context(self):
        """
        Return the context used to render the templates for the email
        subject and body.

        By default, this context includes:

        * All of the validated values in the form, as variables of the
          same names as their fields.

        * The current ``Site`` object, as the variable ``site``.

        * Any additional variables added by context processors (this
          will be a ``RequestContext``).
        
        """
        if not self.is_valid():
            raise ValueError("Cannot generate Context from invalid contact form")
        return RequestContext(self.request,
                              dict(self.cleaned_data,
                                   site=Site.objects.get_current()))

    def clean_recipients(self):
        data = self.cleaned_data['email']
        return data

    def get_message_dict(self):
        """
        Generate the various parts of the message and return them in a
        dictionary, suitable for passing directly as keyword arguments
        to ``django.core.mail.send_mail()``.

        By default, the following values are returned:

        * ``from_email``

        * ``message``

        * ``recipient_list``

        * ``subject``
        
        """
        if not self.is_valid():
            raise ValueError("Message cannot be sent from invalid contact form")
        message_dict = {}
        for message_part in ('from_email', 'message', 'recipient_list', 'subject'):
            if message_part == 'recipient_list':
                attr = [getattr(self, message_part)[0]]
                for mail_tuple in settings.MANAGERS:
                    if mail_tuple[1] not in attr:
                        attr.append(str(mail_tuple[1]))
                attr.append(str(self.clean_recipients()))
                message_dict[message_part] = callable(attr) and attr() or attr
            else:
                attr = getattr(self, message_part)
                message_dict[message_part] = callable(attr) and attr() or attr
    
        return message_dict
    
    def save(self, fail_silently=False):
        """
        Build and send the email message.
        
        """
        '''print self.get_message_dict()'''
        send_mail(fail_silently=fail_silently, **self.get_message_dict())
        
class AkismetContactForm(ApplicationForm):
    """
    Contact form which doesn't add any extra fields, but does add an
    Akismet spam check to the validation routine.

    Requires the setting ``AKISMET_API_KEY``, which should be a valid
    Akismet API key.
    
    """
    def clean_body(self):
        """
        Perform Akismet validation of the message.
        
        """
        if 'body' in self.cleaned_data and getattr(settings, 'AKISMET_API_KEY', ''):
            from akismet import Akismet
            from django.utils.encoding import smart_str
            akismet_api = Akismet(key=settings.AKISMET_API_KEY,
                                  blog_url='http://%s/' % Site.objects.get_current().domain)
            if akismet_api.verify_key():
                akismet_data = { 'comment_type': 'comment',
                                 'referer': self.request.META.get('HTTP_REFERER', ''),
                                 'user_ip': self.request.META.get('REMOTE_ADDR', ''),
                                 'user_agent': self.request.META.get('HTTP_USER_AGENT', '') }
                if akismet_api.comment_check(smart_str(self.cleaned_data['body']), data=akismet_data, build_data=True):
                    raise forms.ValidationError(u"Akismet thinks this message is spam")
        return self.cleaned_data['body']
