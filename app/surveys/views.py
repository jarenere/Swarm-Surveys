# -*- coding: utf-8 -*-
from app import app, db
from flask import Blueprint, request, url_for, flash, redirect, abort, session, g
from flask import render_template
from flask.ext.login import login_user, logout_user, current_user, login_required
from forms import LoginForm
from app.models import Survey, Consent, Section
from app.models import Question, QuestionChoice, QuestionText
from app.models import QuestionYN ,QuestionLikertScale
from app.models import StateSurvey
from app.models import Answer
from flask.ext.wtf import Form
from sqlalchemy.sql import func
from wtforms import TextField, BooleanField, RadioField, IntegerField, HiddenField, DecimalField,StringField
from wtforms import SelectField
from wtforms.validators import Required, Regexp, Optional
from wtforms import ValidationError
from wtforms.fields import Field
from wtforms.validators import StopValidation
from wtforms.widgets import ListWidget, TextInput
import datetime
from . import blueprint
from app.decorators import valid_survey, there_is_stateSurvey
from ..main.errors import ErrorEndDateOut, ErrorExceeded, ErrorTimedOut


@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    '''
    shows all available surveys
    '''
    stmt1 = db.session.query(StateSurvey.survey_id, StateSurvey.status).\
        filter(StateSurvey.user==current_user).subquery()
    
    stmt2 = db.session.query(StateSurvey.survey_id, func.count('*').label('r_count')).\
        filter(StateSurvey.status.op('&')(StateSurvey.FINISH_OK)).\
        group_by(StateSurvey.survey_id).subquery()

    now = datetime.datetime.utcnow()
    #outerjoint Survey and StateSurvey(with the currentUser) and number of user
    # that have made the survey
    surveys = db.session.query(Survey, stmt1.c.status, stmt2.c.r_count).\
        outerjoin(stmt1,Survey.id==stmt1.c.survey_id).\
        outerjoin(stmt2,Survey.id==stmt2.c.survey_id).\
        filter(Survey.startDate<now,Survey.endDate>now).\
        order_by(Survey.startDate)
    return render_template('/surveys/index.html',
        title = 'Index',
        # surveys= [s.Survey for s in surveys],
        surveys = surveys) 

def get_stateSurvey_or_error(id_survey,user,ip = None):
    stateSurvey, status = StateSurvey.getStateSurvey(id_survey,user,ip)
    if status == StateSurvey.NO_ERROR:
        return stateSurvey
    else:
        if status == StateSurvey.ERROR_EXCEEDED:
            raise ErrorExceeded
        if status == StateSurvey.ERROR_TIMED_OUT:
            raise ErrorTimedOut
        if status == StateSurvey.ERROR_END_DATE_OUT:
            raise ErrorEndDateOut
        if status == StateSurvey.ERROR_NO_SURVEY:
            return abort(404)
        return abort(500)    



@login_required
@blueprint.route('/survey/<int:id_survey>', methods=['GET', 'POST'])
@valid_survey
def logicSurvey(id_survey):
    '''
    Function that decides which is the next step in the survey
    '''
    stateSurvey = get_stateSurvey_or_error(id_survey,g.user,request.remote_addr)

    if (stateSurvey.consented == False):
        return redirect(url_for('surveys.showConsent', id_survey = id_survey))
    section = stateSurvey.nextSection()
    if section is None:
        if stateSurvey.status & StateSurvey.FINISH_OK:
            return render_template('/surveys/finish.html', 
                title = 'Finish')
        if stateSurvey.status & StateSurvey.TIMED_OUT:
            return render_template('/survey/error_time_date.html',
                title ='time out')
        if stateSurvey.status & StateSurvey.END_DATE_OUT:
            return render_template('/survey/error_time_date.html',
                title ='End date out')
        print "\n raro\n Status: ", stateSurvey.status
        return abort(500) 
    return redirect (url_for('surveys.showQuestions',id_survey=id_survey,id_section=section.id))

@login_required
@blueprint.route('/survey/<int:id_survey>/consent', methods=['GET', 'POST'])
@blueprint.route('/survey/<int:id_survey>/consent/<int:n_consent>', methods=['GET', 'POST'])
@valid_survey
@there_is_stateSurvey
def showConsent(id_survey,n_consent = 0):
    '''
    Show consent, n_consent is the "position of consent", no id!!
    '''
    
    survey = Survey.query.get(id_survey)
    consents = survey.consents

    if n_consent>consents.count():
        abort (404)

    if consents.count()==0:
        stateSurvey = get_stateSurvey_or_error(id_survey,g.user)
        stateSurvey.accept_consent()
        return redirect(url_for('surveys.logicSurvey',id_survey = id_survey))
    
    if request.method == 'POST' and consents.count()<=n_consent+1:
        stateSurvey = get_stateSurvey_or_error(id_survey,g.user)
        stateSurvey.accept_consent()
        return redirect(url_for('surveys.logicSurvey',id_survey = id_survey))

    if request.method == 'POST' and consents.count()>n_consent+1:
        return redirect(url_for('surveys.showConsent', id_survey = id_survey, n_consent = n_consent+1))


    return render_template('/surveys/consent.html',
        title = survey.title,
        survey = survey,
        consent = survey.consents[n_consent])


def generate_form(questions):
    '''dynamically generates the forms for surveys
    '''
    def frange(x, y, jump):
        '''implement of range to floats:
        '''
        while x < y:
            yield  '{0:g}'.format(float(x))
            x += jump

    def check_answer_expected(self,field):
        '''check if the answer is the expected
        '''
        question = Question.query.get(field.name[1:])
        answer = Answer.query.filter(Answer.user_id==g.user.id,
                Answer.question_id==question.id).first()
        if answer is None:
            answer = Answer (answerText = field.data, user= g.user, question = question)
            answer.globalTime = form["globalTimec"+str(question.id)].data
            answer.differentialTime = form["differentialTimec"+str(question.id)].data
        else:
            answer.answerText = field.data
        db.session.add(answer)
        db.session.commit()
        if not answer.answerAttempt():
            if answer.isMoreAttempt():
                raise ValidationError("Wrong answer")
            else:
                flash("wrong answer, you can continue")
    
    def check_answer_expected_yn(self,field):
        '''check if the answer is the expected
        '''
        question = Question.query.get(field.name[1:])
        answer = Answer.query.filter(Answer.user_id==g.user.id,
                Answer.question_id==question.id).first()
        if answer is None:
            answer = Answer (answerYN = field.data=='Yes', user= g.user, question = question)
            answer.globalTime = form["globalTimec"+str(question.id)].data
            answer.differentialTime = form["differentialTimec"+str(question.id)].data
        else:
            answer.answerYN = field.data=='Yes'
        db.session.add(answer)
        db.session.commit()
        if not answer.answerAttemptYN():
            if answer.isMoreAttempt():
                raise ValidationError("Wrong answer")
            else:
                flash("wrong answer, you can continue")

    def check_subquestion(self,field):
        '''check whether to answer the question or not
        '''
        question = Question.query.get(field.name[1:])
        data = form["c"+str(question.parent.id)].data
        if isinstance (question.parent,QuestionYN):
            if data.lower()==question.condition.value.lower():
                pass
                # raise ValidationError('This field is required.')
            else:
                # nothing to check
                field.errors[:] = []
                raise StopValidation()
        if isinstance (question.parent,QuestionText):
            if question.condition.operation=="<":
                if data<question.condition.value:
                    pass
                else:
                    # nothing to check
                    field.errors[:] = []
                    raise StopValidation()
            if question.condition.operation=="==":
                if data==question.condition.value:
                    pass
                else:
                    # nothing to check
                    field.errors[:] = []
                    raise StopValidation()
            if question.condition.operation==">":
                if int(data)>int(question.condition.value):
                    pass
                else:
                    # nothing to check
                    field.errors[:] = []
                    raise StopValidation()

        if isinstance(question.parent,QuestionChoice):
            if data==question.condition.value:
                pass
            else:
                # nothing to check
                field.errors[:] = []
                raise StopValidation()

    def check_valid_select_field(self,field):
        if field.data=="":
            raise ValidationError("Option not valid")


    class ClassedWidgetMixin(object):
        """Adds the field's name as a class 
        when subclassed with any WTForms Field type.

        Has not been tested - may not work."""
        def __init__(self, *args, **kwargs):
            super(ClassedWidgetMixin, self).__init__(*args, **kwargs)

        def __call__(self, field, **kwargs):
            c = kwargs.pop('class', '') or kwargs.pop('class_', '')
            kwargs['class'] = u'%s %s' % (field.short_name, c)
            print kwargs['class'],"jeje\n"
            return super(ClassedWidgetMixin, self).__call__(field, **kwargs)


    class TagListField(Field):
        widget = TextInput()

        def _value(self):
            if self.data:
                return u', '.join(self.data)
            else:
                return u''

        def process_formdata(self, valuelist):
            if valuelist:
                self.data = [x.strip() for x in valuelist[0].split(',')]
            else:
                self.data = []

        def __call__(self, **kwargs):
            print "jeje\n"
            print super(TagListField, self).__call__(**kwargs)
            return super(TagListField, self).__call__(**kwargs)

    class LikertField(RadioField):
        def __init__(self, label='', validators=None, labelMin="", labelMax="", **kwargs):
            self.labelMin=labelMin
            self.labelMax=labelMax
            super(LikertField, self).__init__(label, validators, **kwargs)

        def __call__(self, **kwargs):
            '''render likert as table
            '''
            from wtforms.widgets.core import html_params, HTMLString
            kwargs.setdefault('id', self.id)
            kwargs.setdefault('class_', " table table-condensed likert")
            html = ['<%s %s>' % ("table", html_params(**kwargs))]
            html.append('<tr>')
            html.append('<td></td>')
            for subfield in self:
                html.append('<td>%s</td>' % (subfield.label))
            html.append('</tr>')
            html.append('<tr>')
            html.append('<td class="type-info">%s</td>' % (self.labelMin))
            for subfield in self:
                    html.append('<td>%s</td>' % (subfield()))
            html.append('<td class="type-info">%s</td>' % (self.labelMax))
            html.append('</tr>')

            html.append('</%s>' % "table")
            return  HTMLString(''.join(html))
            # return super(RadioField, self).__call__(**kwargs)

        def __call1__(self, **kwargs):
            '''render likert as list
            '''
            from wtforms.widgets.core import html_params, HTMLString
            kwargs.setdefault('id', self.id)
            kwargs.setdefault('class_', "likert")
            html = ['<%s %s>' % (self.widget.html_tag, html_params(**kwargs))]
            html.append('<li>%s</li>' % (self.labelMin))

            for subfield in self:
                if self.widget.prefix_label:
                    html.append('<li>%s %s</li>' % (subfield.label, subfield()))
                else:
                    html.append('<li>%s %s</li>' % (subfield(), subfield.label))
            html.append('<li>%s</li>' % (self.labelMax))
            html.append('</%s>' % self.widget.html_tag)
            return  HTMLString(''.join(html))
            # return super(RadioField, self).__call__(**kwargs)

    class MyRadioField(RadioField):
        def __init__(self, label='', validators=None, horizontal=False,**kwargs):
            self.horizontal=horizontal
            super(MyRadioField, self).__init__(label, validators, **kwargs)

        def __call__(self, **kwargs):
            if self.horizontal:
                kwargs.setdefault('class_', "radioField_horizontal")
                self.widget.prefix_label=True
            else:
                kwargs.setdefault('class_', "radio")
                self.widget.prefix_label=False
            print "prefix: ",self.widget.prefix_label
            return super(MyRadioField, self).__call__(**kwargs)





    # class Likert(ClassedWidgetMixin, ListWidget):
    #     pass

    class ClassedTextInput(ClassedWidgetMixin, TextInput):
        pass

    class AnswerForm(Form):
        time = HiddenField('time',default=0)
        
    for question in questions:

        setattr(AnswerForm,"globalTimec"+str(question.id),HiddenField('globalTimec'+str(question.id),default=0))
        setattr(AnswerForm,"differentialTimec"+str(question.id),HiddenField('differentialTimec'+str(question.id),default=0))

        #added "c" to that the key is valid
        #First element must be a string, otherwise fail to valid choice

        if isinstance (question,QuestionYN):
            if question.isSubquestion:
                setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                    choices = [('Yes','Yes'),('No','No')],validators = [check_subquestion]))
            else:
                if question.isExpectedAnswer():
                    setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                        choices = [('Yes','Yes'),('No','No')],validators = [check_answer_expected_yn]))
                elif question.required:
                    setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                        choices = [('Yes','Yes'),('No','No')],validators = [Required()]))
                else:
                    setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                        choices = [('Yes','Yes'),('No','No')],validators = [Optional()]))
        if isinstance (question,QuestionText):
            if question.isSubquestion:
                setattr(AnswerForm,"c"+str(question.id),IntegerField('Answer',
                    validators = [check_subquestion]))
            else:
                if question.required:
                    if question.regularExpression !="":
                        if question.isExpectedAnswer():
                            setattr(AnswerForm,"c"+str(question.id),TextField('Answer',
                                validators=[Required(), Regexp(question.regularExpression,0,question.errorMessage),
                                check_answer_expected]))
                        else:
                            setattr(AnswerForm,"c"+str(question.id),TextField('Answer',
                                validators=[Required(), Regexp(question.regularExpression,0,question.errorMessage)]))
                    elif question.isExpectedAnswer():
                        setattr(AnswerForm,"c"+str(question.id),TextField('Answer',validators = [Required(),
                            check_answer_expected]))
                    elif question.isNumber:
                        setattr(AnswerForm,"c"+str(question.id),IntegerField('Answer'))
                    else:
                        setattr(AnswerForm,"c"+str(question.id),TextField('Answer',validators = [Required()]))
                else:
                    if question.regularExpression !="":
                        setattr(AnswerForm,"c"+str(question.id),TextField('Answer',
                            validators=[Optional(), Regexp(question.regularExpression,0,question.errorMessage)]))
                    elif question.isNumber:
                        setattr(AnswerForm,"c"+str(question.id),IntegerField('Answer',validators = [Optional()]))
                    else:
                        setattr(AnswerForm,"c"+str(question.id),TextField('Answer',validators = [Optional()]))
        if isinstance (question,QuestionChoice):
            if question.is_range:
                list = [(str(index),choice) for index,choice in enumerate(
                    frange(question.range_min,
                        question.range_max+question.range_step,
                        question.range_step))]
            else:
                list = [(str(index),choice) for index, choice in enumerate(question.choices)]
            if question.render == "select":
                list.insert(0,("",""))

            # if question.is_range:
            #         setattr(AnswerForm,"c"+str(question.id),SelectField('Answer', 
            #             choices = list,validators = [check_valid_select_field]))
            if question.isSubquestion:
                    setattr(AnswerForm,"c"+str(question.id),MyRadioField('Answer',
                        horizontal=question.render=="horizontal",
                        choices = list,validators = [check_subquestion]))
            else:
                if question.required:
                    if question.render =="select":
                        setattr(AnswerForm,"c"+str(question.id),SelectField('Answer', 
                            choices = list,validators = [check_valid_select_field]))
                    else:
                        setattr(AnswerForm,"c"+str(question.id),MyRadioField('Answer', 
                            horizontal=question.render=="horizontal",
                            choices = list,validators = [Required()]))
                else:
                    if question.render =="select":
                        setattr(AnswerForm,"c"+str(question.id),SelectField('Answer', 
                            choices = list,validators = [check_valid_select_field]))
                    else:
                        setattr(AnswerForm,"c"+str(question.id),MyRadioField('Answer',
                            horizontal=question.render=="horizontal",
                            choices = list,validators = [Optional()]))

        if isinstance (question, QuestionLikertScale):
            list = [(str(index),choice) for index,choice in enumerate(range(question.minLikert,question.maxLikert+1))]
            if question.required:
                setattr(AnswerForm,"c"+str(question.id),LikertField('Answer', 
                    choices = list,
                    labelMin= question.labelMin,
                    labelMax=question.labelMax,
                    validators = [Required()]))
                # setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                #     choices = list,widget=Likert,validators = [Required()]))
                # AnswerForm["c"+str(question.id)](class_="likert")
                # form.field(class_="text_blob")
            else:
                setattr(AnswerForm,"c"+str(question.id),RadioField('Answer', 
                    choices = list,validators = [Optional()]))

    form = AnswerForm()
    # for question in questions:
    #     if isinstance (question, QuestionLikertScale):
    #         form["c"+str(question.id)].flags.likert=True
    #         form["c"+str(question.id)].flags.labelMin=question.labelMin
    #         form["c"+str(question.id)].flags.labelMax=question.labelMax
    #         form["c"+str(question.id)].class_= "likert"
    #         print form["c"+str(question.id)].class_
    #             # form.c253.flags.likert=True
    return form

def writeQuestion(question, form):
    '''return true if it isn't a subquestion or
        if a question.parent is valid
    '''
    if question.parent is None:
        return True
    else:
        data = form["c"+str(question.parent.id)].data
        if isinstance (question.parent,QuestionYN):
            if data.lower()==question.condition.value.lower():
                return True
            else:
                return False
        if isinstance (question.parent,QuestionText):
            if question.condition.operation=="<":
                if data<question.condition.value:
                    return True
                else:
                    return False
            if question.condition.operation=="==":
                if data==question.condition.value:
                    return True
                else:
                    return False
            if question.condition.operation==">":
                if int(data)>int(question.condition.value):
                    return True
                else:
                    return False
        if isinstance(question.parent,QuestionChoice):
            if data==question.condition.value:
                return True
            else:
                return False

@login_required
@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>', methods=['GET', 'POST'])
@valid_survey
@there_is_stateSurvey
def showQuestions(id_survey, id_section):
    '''
    Show all question of a section
    '''
    stateSurvey = get_stateSurvey_or_error(id_survey,g.user,request.remote_addr)
    section = stateSurvey.nextSection()
    if section is None or section.id !=id_section:
        flash ("access denied")
        return abort (403)
        
    survey = Survey.query.get(id_survey)
    section = Section.query.get(id_section)
    questions = section.questions
   
    form = generate_form(questions)
    if form.validate_on_submit():
        for question in questions:
            if writeQuestion(question, form):
                if isinstance (question,QuestionYN):
                    answer = Answer (answerYN = (form["c"+str(question.id)].data=='Yes'), user= g.user, question = question)
                if isinstance (question,QuestionText):
                    if question.isNumber:
                        if question.isNumberFloat:
                            answer = Answer (answerNumeric = form["c"+str(question.id)].data.replace(",","."), user= g.user, question = question)
                        else:
                            answer = Answer (answerNumeric = form["c"+str(question.id)].data, user= g.user, question = question)
                    else:
                        answer = Answer (answerText = form["c"+str(question.id)].data, user= g.user, question = question)
                if isinstance (question,QuestionChoice):
                    answer = Answer (answerNumeric = form["c"+str(question.id)].data, user= g.user, question = question)
                    answer.answerText = form["c"+str(question.id)].choices[int(form["c"+str(question.id)].data)][1]
                if isinstance (question, QuestionLikertScale):
                    answer = Answer (answerNumeric = form["c"+str(question.id)].data, user= g.user, question = question)
                    answer.answerText = form["c"+str(question.id)].choices[int(form["c"+str(question.id)].data)][1]


                answer.globalTime = form["globalTimec"+str(question.id)].data
                answer.differentialTime = form["differentialTimec"+str(question.id)].data
                db.session.add(answer)
                db.session.commit()

        stateSurvey.finishedSection(form.time.data)
        print "valiendo"
        return redirect(url_for('surveys.logicSurvey',id_survey = id_survey))

    # return render_template('/surveys/showQuestions.html',
    #         title = survey.title,
    #         survey = survey,
    #         section = section,
    #         # form = form,
    #         form = form,
    #         questions = questions,
    #         percent = stateSurvey.percentSurvey()
    #         )
    return render_template('/surveys/likert.html',
            title = survey.title,
            survey = survey,
            section = section,
            # form = form,
            form = form,
            questions = questions,
            percent = stateSurvey.percentSurvey()
            )
