# admin_views.py
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose
from flask_login import current_user
from flask import redirect, url_for, flash

# Custom ModelView class to manage admin access
class MyModelView(ModelView):
    # Use your custom admin base template
    base_template = 'admin/master.html'

    # Restrict access to admin users only
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    # Redirect to login page if access is denied
    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))


# Custom Admin Index View for the admin home page
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        # Custom logic for the index page
        if not current_user.is_authenticated:
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('main_routes.index'))
        
        # Render the custom index template with relevant data
        return self.render('admin/master.html')  # Ensure this template exists in your templates/admin folder