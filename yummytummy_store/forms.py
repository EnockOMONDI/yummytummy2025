from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import Product, Order, Coupon

class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'value': 1})
    )
    update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].label = ''

class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search products...'})
    )

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone',
                  'address', 'area', 'estate', 'building', 'landmark',
                  'order_notes']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area/Neighborhood'}),
            'estate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estate/Community Name'}),
            'building': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment/Building/House Number'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby Recognizable Location'}),
            'order_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Order Notes (Optional)'}),
        }


class PaymentForm(forms.Form):
    PAYMENT_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        initial='mpesa',
        widget=forms.RadioSelect(attrs={'class': 'payment-method-radio'})
    )

    # M-Pesa specific fields
    mpesa_phone = forms.CharField(
        required=False,
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^(07\d{8}|254\d{9})$',
                message='Enter a valid Safaricom number (format: 07XXXXXXXX or 254XXXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Safaricom Number (07XXXXXXXX or 254XXXXXXXXX)'
        })
    )

    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'You must accept the terms and conditions to proceed.'}
    )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        mpesa_phone = cleaned_data.get('mpesa_phone')

        if payment_method == 'mpesa' and not mpesa_phone:
            self.add_error('mpesa_phone', 'Phone number is required for M-Pesa payments')

        return cleaned_data


class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter coupon code',
            'id': 'coupon-code-input'
        })
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()

        try:
            coupon = Coupon.objects.get(code=code, is_active=True)

            # Check if coupon is valid (date range)
            now = timezone.now()
            if now < coupon.valid_from or now > coupon.valid_to:
                raise forms.ValidationError('This coupon has expired.')

            # Check if coupon has reached its usage limit
            if coupon.usage_count >= coupon.usage_limit:
                raise forms.ValidationError('This coupon has reached its usage limit.')

        except Coupon.DoesNotExist:
            raise forms.ValidationError('Invalid coupon code.')

        return code
