# -*- coding: utf-8 -*-

from flask import Blueprint, request, url_for, flash, redirect, abort
from flask import render_template
from forms import SurveyForm, EditConsentForm, SectionForm, QuestionForm
from app.models import Survey, Consent, Section
from app.models import Question, QuestionChoice, QuestionNumerical, QuestionText
from app.models import QuestionYN
from app import app, db
from app.decorators import researcher_required
from flask.ext.login import login_user, logout_user, current_user, login_required

blueprint = Blueprint('researcher', __name__)

@blueprint.route('/')
@blueprint.route('/index')
#@login_required
#@researcher_required
def index():
    surveys = Survey.query.order_by(Survey.created.desc())
    return render_template('/researcher/index.html',
        tittle = 'Survey',
        surveys = surveys)

@blueprint.route('/survey/new', methods = ['GET', 'POST'])
def new():
    form = SurveyForm()
    if form.validate_on_submit():
        survey = Survey( title = form.title.data,
            description = form.description.data)
        db.session.add(survey)
        db.session.commit()
        flash('Your survey have been saved.')
        return redirect(url_for('researcher.editSurvey',id_survey = survey.id))
    return render_template('/researcher/new.html',
        title = 'New survey',
        form = form)

@blueprint.route('/survey/<int:id_survey>', methods = ['GET', 'POST'])
#podrimamos definir la entrada como string del titulo+id:
#ejempo: "esto-es-una-encuesta_123", seria mas legible..
#@blueprint.route('/edit/tittle_<int:id>'
def editSurvey(id_survey):
    #get survey
    survey = Survey.query.get(id_survey)
    sections = survey.sections.all()
    form = SurveyForm()
    if form.validate_on_submit():
        survey.title = form.title.data
        survey.description = form.description.data
        db.session.add(survey)
        db.session.commit()
        flash('Your changes have been saved.')
    elif request.method != "POST":
        form.title.data = survey.title
        form.description.data = survey.description
    return render_template('/researcher/editSurvey.html',
        title = survey.title,
        form = form,
        survey = survey,
        sections = sections)


@blueprint.route('/edit2/<int:id_survey>', methods = ['GET', 'POST'])
#podrimamos definir la entrada como string del titulo+id:
#ejempo: "esto-es-una-encuesta_123", seria mas legible..
#@blueprint.route('/edit/tittle_<int:id>'
def editSurvey2(id_survey):
    #get survey
    survey = Survey.query.get(id_survey)
    #survey = Survey.query.filter(Survey.id == id)
    sections = survey.sections.all()
    form = EditSurveyForm()
    if form.validate_on_submit():
        survey.title = form.title.data
        survey.description = form.description.data
        db.session.add(survey)
        db.session.commit()
        flash('Your changes have been saved.')
    elif request.method != "POST":
        form.title.data = survey.title
        form.description.data = survey.description
    return render_template('/researcher/editSurvey2.html',
        title = survey.title,
        form = form,
        survey = survey,
        sections = sections)


@blueprint.route('/survey/<int:id_survey>/consent/add', methods = ['GET', 'POST'])
#podrimamos definir la entrada como string del titulo+id:
#ejempo: "esto-es-una-encuesta_123", seria mas legible..
def addConsent(id_survey):
    form = EditConsentForm()
    survey = Survey.query.get(id_survey)
    if survey == None:
        flash('Survey not found.')
        return redirect(url_for('researcher.index'))
    else:
        consents = survey.consents.all()

    if form.validate_on_submit():
        consent = Consent(text = form.text.data,
            survey = survey)
        db.session.add(consent)
        db.session.commit()
        flash('Adding consent.')
        return redirect(url_for('researcher.addConsent',id_survey = survey.id))
 
    return render_template('/researcher/consents.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        consents = consents,
        addConsent = True)

@blueprint.route('/survey/<int:id_survey>/consent/<int:id_consent>/delete')
def deleteConsent(id_survey,id_consent):
    consent = Consent.query.filter(Consent.survey_id == id_survey, Consent.id == id_consent).first()
    if consent != None:
        db.session.delete(consent)
        db.session.commit()
        flash('consent removed')
        return redirect(url_for('researcher.addConsent',id_survey = id_survey))
    else:
        flash('consent wrong') 
        return redirect(url_for('researcher.addConsent',id_survey = id_survey))


@blueprint.route('/survey/<int:id_survey>/consent/<int:id_consent>', methods = ['GET', 'POST'])
def editConsents(id_survey, id_consent):
    consent = Consent.query.filter(Consent.survey_id == id_survey, Consent.id == id_consent).first()
    if consent == None:
        flash('Consent wrong') 
        return redirect(url_for('researcher.addConsent',id_survey = id_survey))
    form = EditConsentForm()
    if form.validate_on_submit():
        consent.text = form.text.data
        db.session.add(consent)
        db.session.commit()
        flash('Editing consent')
        return redirect(url_for('researcher.addConsent',id_survey = id_survey))
    elif request.method != "POST":
        form.text.data = consent.text
        consents = Consent.query.filter(Consent.survey_id == id_survey)
    return render_template('/researcher/consents.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        consents = consents,
        editConsent = True)

@blueprint.route('/survey/<int:id_survey>/section/', methods = ['GET', 'POST'])
def addSection(id_survey):
    form = SectionForm()
    survey = Survey.query.get(id_survey)
    if survey == None:
        flash('Survey not found.')
        return redirect(url_for('researcher.index'))
    else:
        sections = survey.sections.all()
    if form.validate_on_submit():
        section = Section(title = form.title.data,
            description = form.description.data,
            sequence = form.sequence.data,
            percent = form.percent.data,
            survey = survey
            )
        db.session.add(section)
        db.session.commit()
        flash('Adding section.')
        return redirect(url_for('researcher.editSurvey',id_survey = survey.id))
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        sections = sections,
        #add = true, you is adding a new section
        addSection = True)

@blueprint.route('/edit/<int:id_survey>/section/<int:id_section>', methods = ['GET', 'POST'])
def editSection(id_survey, id_section):
    section = Section.query.filter(Section.survey_id == id_survey, Section.id == id_section).first()
    if section == None:
        flash('Section wrong') 
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))
    form = SectionForm()
    print section.title
    subsections = section.children.all()
    if form.validate_on_submit():
        section.title = form.title.data
        section.description = form.description.data
        section.sequence = form.sequence.data
        section.percent = form.percent.data
        db.session.add(section)
        db.session.commit()
        flash('Editing consent')
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))
    elif request.method != "POST":
        form.title.data = section.title
        form.description.data = section.description
        form.sequence.data = section.sequence
        form.percent.data = section.percent
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        sections = subsections,
        #add = true, you is adding a new section, add = False you is editing a section
        editSection = True,
        id_section = id_section)

@blueprint.route('/survey/<int:id_survey>/deleteSection/<int:id_section>')
def deleteSection(id_survey,id_section):
        #
        #CUANDO TENGA SUBSECCIONES Y ENCUESTAR, EL ELIMINAR NO ES TRIVIAL
        #
    section = Section.query.filter(Section.survey_id == id_survey, Section.id == id_section).first()
    if section != None:
        #el consentimiento pertence a esa encuesta
        db.session.delete(section)
        db.session.commit()
        flash('Section removed')
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))
    else:
        flash('Section wrong') 
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))

@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/subSection', methods = ['GET', 'POST'])
def addSubSection(id_survey, id_section):
    section = Section.query.filter(Section.survey_id == id_survey, Section.id == id_section).first()
    if section == None:
        flash('Section wrong') 
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))

    form = SectionForm()
    subsections = section.children.all()

    if form.validate_on_submit():
        section = Section(title = form.title.data,
            description = form.description.data,
            sequence = form.sequence.data,
            percent = form.percent.data,
            parent = section)

        db.session.add(section)
        db.session.commit()
        flash('Adding subsection.')
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))
    
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        sections = subsections,
        #add = true, you is adding a new section, add = False you is editing a section
        addSubSection = True)

@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/subSection/<int:id_subSection>', methods = ['GET', 'POST'])
def editSubSection(id_survey, id_section,id_subSection):
    '''
    #:id_survey: id of Survey
    #:id_section: id of parent section, maybe can be deleted
    #:id_subSection: id of secction to modify
    '''
    section = Section.query.filter(Section.id == id_subSection, Section.parent_id == id_section).first()
    if section == None:
        flash('Section wrong') 
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))
    form = SectionForm()
    subsections = section.children
    print section.title
    if form.validate_on_submit():
        section.title = form.title.data
        section.description = form.description.data
        section.sequence = form.sequence.data
        section.percent = form.percent.data
        db.session.add(section)
        db.session.commit()
        flash('Editing consent')
        return redirect(url_for('researcher.editSurvey',id_survey = id_survey))
    elif request.method != "POST":
        form.title.data = section.title
        form.description.data = section.description
        form.sequence.data = section.sequence
        form.percent.data = section.percent
    return render_template('/researcher/addEditSection.html',
        title = "consent",
        form = form,
        id_survey = id_survey,
        sections = subsections,
        #add = true, you is adding a new section, add = False you is editing a section
        addSubSection = True,
        id_subSection = id_subSection)


@blueprint.route('/survey/<int:id_survey>/section/<int:id_section>/addQuestion', methods = ['GET', 'POST'])
def addQuestion(id_survey, id_section):
    section = Section.query.filter(Section.survey_id == id_survey, Section.id == id_section).first()
    if section == None:
        flash('Section wrong') 
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))
    form = QuestionForm()
    
    if form.validate_on_submit():
        if form.questionType.data =='YES/NO':
            question = QuestionYN()
        if form.questionType.data == 'Numerical':
            question = QuestionNumerical()
        if form.questionType.data == 'Text':
            question = QuestionText()
        if form.questionType.data == 'Choice':
            l = [form.answer1.data,
            form.answer2.data,
            form.answer3.data,
            form.answer4.data,
            form.answer5.data,
            form.answer6.data,
            form.answer7.data,
            form.answer8.data,
            form.answer9.data]
            question = QuestionChoice(choices = l[0:int(form.numberFields.data)])
        question.text = form.text.data
        question.required = form.required.data
        question.registerTime = form.registerTime.data
        question.section = section
        db.session.add(question)
        db.session.commit()
        flash('Adding question')
        return redirect(url_for('researcher.editSection',id_survey = id_survey, id_section = id_section))
    
    return render_template('/researcher/addEditQuestion.html',
        title = "Question",
        form = form,
        id_survey = id_survey,
        section = section)