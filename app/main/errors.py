from flask import render_template, request
from . import blueprint

class MyCustom404(Exception):
    pass


@blueprint.app_errorhandler(403)
def forbidden(error):
    return render_template('403.html',title = 'Forbidden'), 403

@blueprint.app_errorhandler(404)
def internal_error(error):
    return render_template('404.html', title='File Not Found'), 404

@blueprint.app_errorhandler(500)
def internal_error(error):
    return render_template('500.html', title='Internal Server Error'), 500

@blueprint.app_errorhandler(600)
def internal_error(error):
    return render_template('600.html', title='Finished Survey'), 600

@blueprint.app_errorhandler(MyCustom600)
def special_page_not_found(error):
    return render_template("600.html"), 600