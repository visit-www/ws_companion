from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from werkzeug.utils import secure_filename
from flask import redirect, url_for, flash, request
from flask_login import current_user
import os
from . import db
import shutil
from datetime import datetime, timezone

class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    form_excluded_columns = ['filepath']

    form_overrides = {
        'file': FileUploadField
    }

    form_args = {
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),
            'allow_overwrite': False,
            'allowed_extensions': ['txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 'pptx', 'html', 'md'],
        }
    }

    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        file_path = os.path.join(target_folder, filename)
        model.filepath = file_path

    def custom_delete_file(self, model):
        trash_folder = os.path.join('trash')
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d') 
        current_date_folder = os.path.join(trash_folder, date)
        os.makedirs(current_date_folder, exist_ok=True)

        if model.filepath and os.path.exists(model.filepath):
            try:
                shutil.move(model.filepath, current_date_folder)
                model.filepath = None
                model.file = None
            except OSError as e:
                flash(f'Error deleting file: {str(e)}', 'danger')

    def on_model_change(self, form, model, is_created):
        upload_file = bool(form.file.data)
        
        try:
            if is_created:
                if upload_file:
                    self.custom_upload_file(form, model)
                    db.session.add(model)
                    db.session.commit()
                else:
                    db.session.add(model)
                    db.session.commit()
            else:
                file_present = bool(model.file)
                delete_file = '_file-delete' in request.form

                if file_present:
                    if os.path.exists(os.path.join('dummy_folder', model.file)):
                        if model.filepath:
                            orig_file_path = model.filepath
                            file_name = str(model.file)
                            trash_folder = os.path.join('trash')
                            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                            current_date_folder = os.path.join(trash_folder, date)
                            os.makedirs(current_date_folder, exist_ok=True)
                            shutil.move(orig_file_path, current_date_folder)
                            self.custom_upload_file(form, model)
                            db.session.add(model)
                            db.session.commit()
                        else:
                            self.custom_upload_file(form, model)
                            db.session.add(model)
                            db.session.commit()
                    else:
                        orig_file_path = model.filepath
                        file_name = str(model.file)
                        category = model.category.value if hasattr(model.category, 'value') else model.category
                        module = model.module.value if hasattr(model.module, 'value') else model.module
                        new_folder = os.path.join("files", category, module)
                        new_file_path = os.path.join(new_folder, file_name)
                        os.makedirs(new_folder, exist_ok=True)
                        if orig_file_path != new_file_path:
                            shutil.move(orig_file_path, new_folder)
                            file_path = os.path.join(new_folder, file_name)
                            model.filepath = file_path
                            db.session.add(model)
                            db.session.commit()
                        else:
                            db.session.add(model)
                            db.session.commit()
                else:
                    if delete_file:
                        self.custom_delete_file(model)
                        db.session.add(model)
                        db.session.commit()
                    else:
                        db.session.add(model)
                        db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during the update: {e}", 'danger')

    def on_model_delete(self, model):
        self.custom_delete_file(model)
        db.session.delete(model)
        db.session.commit()