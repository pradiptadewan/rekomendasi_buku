from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    # Tambahkan field email
    email = forms.EmailField(required=True, help_text='Wajib diisi. Kami tidak akan membagikan email Anda.')

    class Meta(UserCreationForm.Meta):
        # Gunakan model User bawaan Django
        model = User
        # Tentukan field yang akan ditampilkan di form, tambahkan 'email'
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        # Tambahkan kelas CSS 'form-input' ke semua field agar sesuai dengan style Anda
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input'