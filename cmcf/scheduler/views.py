# Create your views here.

from urllib import quote
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.create_update import delete_object
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic.create_update import delete_object
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.encoding import smart_str
from django.core.management import call_command

import datetime
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta

import re, string
from django.db.models import Q
from django.conf import settings

from scheduler.models import *
from calendar import Calendar, HTMLCalendar
from decorators import protectview

WARNING = "This is a last-minute change. It will take a few moments to send a notification e-mail to the Users Office and to beamline staff."

def staff_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated() and u.is_staff,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

@protectview
def staff_calendar(request, day=None, template='scheduler/admin_schedule_week.html'):
    return current_week(request, day, template, staff=True)

@staff_login_required
def admin_scheduler(request, day=None, template='scheduler/admin_schedule_week.html'):
    return current_week(request, day, template, staff=True, admin=True, title="Beamtime Scheduler")

@staff_login_required
def edit_visit(request, id, model, form, template='wp-root.html'):
    form_info = {'title': 'Edit Beamline Visit',
                 'action':  reverse('bl-edit-visit', args=[id]),
                 'save_label': 'Save',
                 'enctype' : 'multipart/form-data',
                 }
    today = datetime.now().date()
    this_monday = today - timedelta(days=datetime.now().date().weekday())
    next_monday = this_monday + timedelta(days=7)
    etime = datetime(this_monday.year, this_monday.month, this_monday.day, 13, 30)
    
    visit = Visit.objects.get(pk__exact=id)
    mod_msg = ''
    if request.method == 'POST':
        if visit.start_date <= next_monday and visit.start_date >= today:
            for field in ['proposal', 'start_date', 'end_date', 'first_shift', 'last_shift', 'beamline']:
                if str(request.POST.get(field, None)) != str(visit.__dict__[((field == 'proposal' or field == 'beamline') and '%s_id' % field) or field]):
                    msg = string.capwords(field.replace('_', ' '))
                    mod_msg = mod_msg and '%s AND %s' % (mod_msg, msg) or msg
        frm = form(request.POST, instance=visit)
        if frm.is_valid():
            frm.save()
            if mod_msg and visit.modified > etime:
                call_command('notify', visit.pk, 'MODIFIED: ', 'Changed %s.' % mod_msg) 
            message =  '%(name)s modified' % {'name': smart_str(model._meta.verbose_name)}
            request.user.message_set.create(message = message)
            return render_to_response('scheduler/refresh.html', context_instance=RequestContext(request))
        else:
            return render_to_response(template, {
            'info': form_info, 
            'form' : frm, 
            }, context_instance=RequestContext(request))
    else:
        form.warning_message = (visit.start_date <= next_monday and visit.start_date >= today and datetime.now() > etime and  WARNING) or None
        frm = form(instance=visit, initial=dict(request.GET.items())) # casting to a dict pulls out first list item in each value list
        return render_to_response(template, {
        'info': form_info, 
        'form' : frm,
        }, context_instance=RequestContext(request))
    
@staff_login_required
def delete_object(request, id, model, form, template='wp-root.html'):
    obj = model.objects.get(pk__exact=id)
    today = datetime.now().date()
    this_monday = today - timedelta(days=datetime.now().date().weekday())
    next_monday = this_monday + timedelta(days=7)
    etime = datetime(this_monday.year, this_monday.month, this_monday.day, 13, 30)
    
    form_info = {        
        'title': 'Delete %s?' % obj,
        'sub_title': 'The %s (%s) will be deleted' % ( model._meta.verbose_name, obj),
        'action':  request.path,
        'message': 'Are you sure you want to delete this visit?',
        'save_label': 'Delete'
        }
    if request.method == 'POST':
        frm = form(request.POST, instance=obj)
        if frm.is_valid():
            message =  '%(name)s deleted' % {'name': smart_str(model._meta.verbose_name)}
            if model == Visit:
                if obj.start_date <= next_monday and obj.start_date >= today and obj.modified > etime:
                    call_command('notify', obj.pk, 'DELETED: ')
            obj.delete()
            request.user.message_set.create(message = message)
            return render_to_response('scheduler/refresh.html', context_instance=RequestContext(request))
        else:
            return render_to_response(template, {
            'info': form_info, 
            'form' : frm, 
            }, context_instance=RequestContext(request))
    else:
        frm = form(instance=obj, initial=dict(request.GET.items())) # casting to a dict pulls out first list item in each value list
        if model == Visit:
            form.warning_message = (obj.start_date <= next_monday and obj.start_date >= today and datetime.now() > etime  and WARNING) or None
        return render_to_response(template, {
            'info': form_info, 
            'form' : frm,
            }, context_instance=RequestContext(request))
    

@staff_login_required
def add_object(request, model, form, template='wp-root.html'):
    """
    A view which displays a Form of type ``form`` using the Template
    ``template`` and when submitted will create a new object of type ``model``.
    """
    form_info = {'title': 'Add New %s' % model.__name__,
                 'action':  request.path,
                 'save_label': 'Submit',
                 'enctype' : 'multipart/form-data',
                 }
    today = datetime.now().date()
    this_monday = today - timedelta(days=datetime.now().date().weekday())
    next_monday = this_monday + timedelta(days=7)
    etime = datetime(this_monday.year, this_monday.month, this_monday.day, 13, 30)

    if request.method == 'POST':
        frm = form(request.POST)
        if frm.is_valid():
            new_obj = frm.save()
            if model in [Visit, Stat]:
                start_date = new_obj.start_date or request.POST.get('start_date')
                first_shift = int(new_obj.first_shift) or int(request.POST.get('first_shift'))
                ns = int(request.POST.get('num_shifts'))
                extra_shifts = ( ns - ( 3 - first_shift ))
                extra_days = extra_shifts/3 + ( bool(extra_shifts%3) and 1 or 0 )
                end_date = datetime.strptime(str(start_date), '%Y-%m-%d') + timedelta(days=extra_days)
                
                new_obj.start_date = start_date
                new_obj.first_shift = first_shift
                new_obj.last_shift = ( first_shift + ns - 1 ) % 3                  
                new_obj.end_date = end_date.date()
                new_obj.save()
                if model == Visit:
                    if new_obj.start_date <= next_monday and new_obj.start_date >= today and new_obj.modified > etime:
                        call_command('notify', new_obj.pk, 'ADDED: ')
            message =  'New %(name)s added' % {'name': smart_str(model._meta.verbose_name)}
            request.user.message_set.create(message = message)
            return render_to_response('scheduler/refresh.html', context_instance=RequestContext(request))
        else:
            return render_to_response(template, {
                'info': form_info,
                'form': frm,
                }, context_instance=RequestContext(request))
    else:
        frm = form(initial=request.GET.items())
        if model in [Visit, Stat]:
            start_date = datetime.strptime(str(request.GET.get('start_date')), '%Y-%m-%d').date()
            if model == Visit:
                form.warning_message = (start_date <= next_monday and start_date >= today and datetime.now() > etime and WARNING) or None
        return render_to_response(template, {
            'info': form_info, 
            'form': frm, 
            }, context_instance=RequestContext(request))

@staff_login_required    
def upload_modes(request, model, form, template='wp-root.html'):
    """A generic view which displays a Form of type ``form`` using the Template
    ``template`` and when submitted will create new data using the LimsWorkbook
    class
    """
    form_info = {
        'title': 'Upload %s' % object_type,
        'action':  request.path,
        'add_another': False,
        'save_label': 'Upload',
        'enctype' : 'multipart/form-data',
    }
    if request.method == 'POST':
        frm = form(request.POST, request.FILES)
        if frm.is_valid():
            # saving valid data to the database can fail if duplicates are found. in this case
            # we need to manually rollback the transaction and return a normal rendered form error
            # to the user, rather than a 500 page
            try:
                # Read the schedule table from the CLS website, and save the information to the db.
                page = urllib2.urlopen("http://www.lightsource.ca/operations/schedule.php")
                soup = BeautifulSoup(page)
                t = soup.find("table", "excel1")
                dat = [ map(str, row.findAll("td")) for row in t.findAll("tr") ]
                mode_calendar = []
                dates = []
                w = 0
            
                # Strip empty and formatting rows
                for x in range(len(dat)):
                    z = 0
                    for y in range(len(dat[w])):
                        if dat[w][z].endswith('&nbsp;</td>'):
                            dat[w].pop(z)
                        else:
                            dat[w][z] = ' '.join(' '.join(dat[w][z].split('>')[1:]).split('<')[:-1])
                            z += 1
                    if dat[w]:
                        w += 1
                    else:
                        dat.pop(w)
            
                if dat[0][0][:2] == 'Su':   
                    dat.pop(0)
            
                month = "Jan"
                year = "1999"
            
                # get initial month and year from the table
                for i in range(0, len(dat)):
                    if dat[i][0][0] not in [0,1,2,3,4,5,6,7,8,9]:
                        month = dat[i][0].split(" ")[0][:3]
                        year = dat[i][0].split(" ")[-1][-4:]
                        break
            
                x = 0
                while x is not len(dat):
                    if len(dat[x]) < 7:
                        dat.pop(x)
                    else:
                        empty = True
                        for y in range(len(dat[x])):
                            if len(dat[x][y]):
                                empty = False
                        if empty:
                            dat.pop(x)
                        else:
                            x = x+1
            
                for x in range(len(dat)):
                    if dat[x][0][2:3] != ':':
                        if len(dat[x][0]) > 8:
                            for y in range(1,8):
                                if len(dat[x][y]) == 1:
                                    month = dat[x][0][:3]
                                    year = dat[x][0][-4:]
                                    dat[x][y] = month + '/0' + dat[x][y].split(' ')[0] + '/' + year
                                if len(dat[x][y]) == 2:
                                    dat[x][y] = month + '/' + dat[x][y].split(' ')[0] + '/' + year
                        else:
                            for y in range(len(dat[x])):
                                if len(dat[x][y]) == 1:
                                    dat[x][y] = '0' + dat[x][y]
                                if month:
                                    dat[x][y] = month + '/' + dat[x][y].split(' ')[0] + '/' + year
            
                for x in range(len(dat)):
                    if len(dat[x]) > 7:
                        dat[x].pop(0)
            
                no_print = False
                
                #GOOD
                        
                for z in range(len(dat)/4):
                    for x in range(0,7):
                        mode_day = []
                        for y in range(0,4):
                            mode_day.append(dat[y][x])
                        dates.append(mode_day[0])
                        mode_calendar.append(mode_day)
                    if x == 6:
                        for i in range(0,4):
                            dat.pop(0)
            
                for x in range(len(mode_calendar)):
                    mode_calendar[x][1] = mode_calendar[x][2]
                    mode_calendar[x][2] = mode_calendar[x][3]
                    if x != len(mode_calendar)-1:
                        mode_calendar[x][3] = mode_calendar[x+1][1]
                    day_status = WebStatus(date=dates[x], status1=mode_calendar[x][1], status2=mode_calendar[x][2], status3=mode_calendar[x][3])
                    if WebStatus.objects.filter(date=day_status.date):
                        no_print = True
                    if no_print:
                        #print "Skipping", day_status.date
                        no_print=False
                    else:
                        #print "Saving...", day_status.date
                        day_status.save()
            
                return mode_calendar

            except IntegrityError:
                transaction.rollback()
                frm.add_excel_error('This data has been uploaded already')
                return render_to_response(template, {'form': frm, 'info': form_info}, context_instance=RequestContext(request))
        else:
            return render_to_response(template, {'form': frm, 'info': form_info}, context_instance=RequestContext(request))
    else:
        frm = form(initial={'project': project.pk})
        return render_to_response(template, {'form': frm, 'info': form_info}, context_instance=RequestContext(request))


def get_one_week(dt=None):
    if dt is None:
        dt = datetime.now().date()
        
    # start on first day of week
    wk_dt = dt - timedelta(days=dt.weekday())
    week = [wk_dt]
    for i in range(6):
        wk_dt = wk_dt + timedelta(days=1)
        week.append( wk_dt )
    return week
        
def combine_shifts(shifts, ids=False):
    new_shifts = [[],[],[]]
    for shift in shifts:
        for i in range(3):
            if shift[i] is not None:
                if new_shifts[i] and (new_shifts[i] == ['FacilityRepair'] or shift[i] == 'FacilityRepair') : new_shifts[i][0] += ' '+shift[i]
                if not new_shifts[i]: new_shifts[i].append(shift[i])
    if not ids:
        for i in range(3):
            new_shifts[i] = ','.join(new_shifts[i])
    return new_shifts

def current_week(request, day=None, template='scheduler/schedule_week.html', admin=False, staff=False, title=''):
    today = datetime.now()
    if day is not None:
        dt = datetime.strptime(day, '%Y-%m-%d').date()
    else:
        dt = today.date()
    
    this_wk = get_one_week(dt)
    prev_wk_day = (dt + timedelta(weeks=-1)).strftime('%Y-%m-%d')
    next_wk_day = (dt + timedelta(weeks=1)).strftime('%Y-%m-%d')
    shift = ( today.time() < time(8) and 2 ) or ( today.time() > time(16) and 1 ) or 0 
    if shift == 2: today = today - timedelta(days=1)

    calendar = []    
    bl_keys = []
    bl_week = {}
    beamlines = Beamline.objects.all()
    week_personnel = OnCall.objects.week_occurences(dt)
    modes = Stat.objects.filter(start_date__lte=this_wk[-1],end_date__gte=this_wk[0]).order_by('-pk')

    for bl in beamlines:
        bl_week[bl.name] = bl.visit_set.week_occurences(dt)
        bl_keys.append(bl.name)
    
    for day in this_wk:
        key = day.strftime('%a %b/%d')
        shifts = {}
        date = day.strftime('%Y-%m-%d')
        
        mode_shifts = []
        beammode = []
        for current_mode in modes:
            beammode.append(current_mode.get_shifts(day))
        beammode = [m for m in beammode if m != [None, None, None]]
        mode_shifts.append(combine_shifts(beammode))
        for blkey, blvis in bl_week.items():
            shifts[blkey] = []

            for vis in blvis:
                shifts[blkey].append(vis.get_shifts(day, True))

        day_shifts = []
        for blkey in bl_keys:
            day_shifts.append(combine_shifts(shifts[blkey], True))

        on_call = [o for o in week_personnel if o.date == day]
        mode_day = []

        if day is not None:
            yr = str(day)
        else:
            yr = str(datetime.now().date())
        if WebStatus.objects.filter(date=key.split(' ')[1] + '/' + yr[:4]):
            stat = WebStatus.objects.get(date=key.split(' ')[1] + '/' + yr[:4])
            mode_day.append(stat.status1)
            mode_day.append(stat.status2)
            mode_day.append(stat.status3)
                
        calendar.append((key, day_shifts, on_call, mode_shifts, mode_day, date))

    return render_to_response(
        template, 
        {
            'beamlines': beamlines,
            'calendar':  calendar,
            'next_week': next_wk_day,
            'prev_week': prev_wk_day,
            'admin':     admin,
            'staff':     staff,
            'today':    [(today).strftime('%a %b/%d'), shift],
            'title':    title,
        },
        context_instance=RequestContext(request),
    )
    
def contact_legend(request):
    support_list = []
    for person in SupportPerson.objects.all():
            support_list.append(person)

    return render_to_response(     
   	'contacts/contact_legend.html', 
        {'contact_list': support_list},
        )

def contact_list(request):
    support_list = []
    categories = []
    for category in SupportPerson.STAFF_CHOICES:
        categories.append(category)
    for person in SupportPerson.objects.all():
            support_list.append(person)

    return render_to_response(     
   	'contacts/contact_list.html', 
        {
            'contact_list': support_list,
            'categories': categories,
        },
        )


    