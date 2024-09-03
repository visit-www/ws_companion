from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from flask_wtf.file import FileAllowed, FileRequired
from werkzeug.utils import secure_filename
from flask import redirect, url_for, flash
from flask_login import current_user
import os
from . import db

class MyModelView(ModelView):
    # Restrict access to admin users only
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    # Redirect to login page if access is denied
    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    # Use FileUploadField for file handling
    form_overrides = {
        'file': FileUploadField  # Assuming the file column is named 'file'
    }

    form_args = {
        'file': {  # Matching the column name to ensure proper handling
            'label': 'Select File',
            'base_path': os.path.join("'uploads',  # Ensure this is the correct upload directory
            'allow_overwrite': False,
            'allowed_extensions': ['txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 'pptx', 'html', 'md'],
        }
    }

    # This method is called when a model is saved
    def on_model_change(self, form, model, is_created):
        if form.file.data:
            # Extract category and module as values, ensuring they are not treated as strings
            category = model.category.value if hasattr(model.category, 'value') else model.category
            module = model.module.value if hasattr(model.module, 'value') else model.module
            
            # Secure and determine the save path for the file
            filename = secure_filename(form.file.data.filename)
            target_dir = os.path.join('files', category, module)  # Ensure the directory path is constructed correctly
            
            # Create directories if they do not exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(target_dir, filename)
            form.file.data.save(file_path)  # Save the file using the save method of the file object
            
            # Update the model's filepath and commit changes
            model.filepath = file_path  # This sets the path to the saved file in the filepath column
            
            # Add the model to the session and commit
            db.session.add(model)
            db.session.commit()