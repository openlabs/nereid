# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool
from flask_wtf import Form
from flask_wtf.csrf import generate_csrf
from wtforms import StringField
from wtforms.validators import DataRequired
from nereid import route


class MyForm(Form):
    name = StringField("Name", validators=[DataRequired()])


class TestModel(ModelSQL):
    """A Tryton model which uses Pagination which could be used for
    testing."""
    __name__ = "nereid.test.test_model"

    name = fields.Char("Name")

    @classmethod
    @route('/fail-with-transaction-error')
    def fail_with_transaction_error(cls):
        """
        Just fail raising a DatabaseOperationalError
        """
        from trytond import backend
        DatabaseOperationalError = backend.get('DatabaseOperationalError')
        raise DatabaseOperationalError()

    @classmethod
    @route('/test-lazy-renderer')
    def test_lazy_renderer(cls):
        """
        Just call the home method and modify the headers in the return value
        """
        rv = Pool().get('nereid.website').home()
        rv.headers['X-Test-Header'] = 'TestValue'
        rv.status = 201
        return rv

    @classmethod
    @route('/gen-csrf', methods=['GET'])
    def gen_csrf(cls):
        """
        return a csrf token
        """
        return '%s' % generate_csrf()

    @classmethod
    @route('/test-csrf', methods=['POST'])
    def test_csrf(cls):
        """
        Just return 'OK' if post request succesed
        """
        form = MyForm()
        if form.validate_on_submit():
            return 'Success'
        return 'Failure'

    @classmethod
    @route('/test-csrf-exempt', methods=['POST'], exempt_csrf=True)
    def test_csrf_exempt(cls):
        """
        Just return 'OK' if post request succesed
        """
        form = MyForm(csrf_enabled=False)
        if form.validate_on_submit():
            return 'Success'
        return 'Failure'
