from decimal import Decimal

from django import forms
from django.forms.models import BaseInlineFormSet
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget

from .models import Category, Coupon, Ingredient, Product, Recipe, RecipeCategory, Refund
from .rich_text import sanitize_rich_text


class SanitizedRichTextMixin:
    rich_text_fields = ()

    def clean(self):
        cleaned = super().clean()
        for field_name in self.rich_text_fields:
            if field_name in cleaned:
                cleaned[field_name] = sanitize_rich_text(cleaned[field_name])
        return cleaned


class ArrayJSONField(forms.JSONField):
    """Keep JSON arrays as lists for Unfold's multi-value array widget."""

    def prepare_value(self, value):
        if isinstance(value, (list, tuple)):
            return list(value)
        return super().prepare_value(value)

    def bound_data(self, data, initial):
        if isinstance(data, (list, tuple)):
            return list(data)
        return super().bound_data(data, initial)


class CategoryAdminForm(SanitizedRichTextMixin, forms.ModelForm):
    description = forms.CharField(required=False, widget=WysiwygWidget())
    rich_text_fields = ('description',)

    class Meta:
        model = Category
        fields = '__all__'


class IngredientAdminForm(SanitizedRichTextMixin, forms.ModelForm):
    description = forms.CharField(required=False, widget=WysiwygWidget())
    rich_text_fields = ('description',)

    class Meta:
        model = Ingredient
        fields = '__all__'


class ProductAdminForm(SanitizedRichTextMixin, forms.ModelForm):
    description = forms.CharField(widget=WysiwygWidget())
    rich_text_fields = ('description',)

    class Meta:
        model = Product
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_featured') and not cleaned.get('feature_type'):
            self.add_error('feature_type', 'Choose a feature label for featured products.')
        if cleaned.get('track_inventory') and not self.instance.variants.exists() and cleaned.get('stock_quantity', 0) < 0:
            self.add_error('stock_quantity', 'Stock cannot be negative.')
        return cleaned


class ProductIngredientInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        percentages = []
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue
            percentage = form.cleaned_data.get('percentage')
            if percentage is not None:
                percentages.append(percentage)

        if percentages and sum(percentages, Decimal('0.00')) != Decimal('100.00'):
            raise forms.ValidationError('Ingredient percentages must total exactly 100%, or all percentages must be blank.')


class CouponAdminForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'


class RecipeCategoryAdminForm(SanitizedRichTextMixin, forms.ModelForm):
    description = forms.CharField(required=False, widget=WysiwygWidget())
    rich_text_fields = ('description',)

    class Meta:
        model = RecipeCategory
        fields = '__all__'


class RecipeAdminForm(SanitizedRichTextMixin, forms.ModelForm):
    description = forms.CharField(widget=WysiwygWidget())
    preview_content = forms.CharField(required=False, widget=WysiwygWidget())
    ingredients = ArrayJSONField(
        widget=ArrayWidget(),
        help_text='Add one ingredient per row. Dragging is not required; rows are saved in display order.',
    )
    instructions = ArrayJSONField(
        widget=ArrayWidget(),
        help_text='Add one preparation step per row in the order customers should follow.',
    )
    rich_text_fields = ('description', 'preview_content')

    class Meta:
        model = Recipe
        fields = '__all__'

    def clean_ingredients(self):
        ingredients = self.cleaned_data['ingredients']
        values = [str(value).strip() for value in ingredients if str(value).strip()]
        if not values:
            raise forms.ValidationError('Add at least one ingredient.')
        return values

    def clean_instructions(self):
        instructions = self.cleaned_data['instructions']
        values = [str(value).strip() for value in instructions if str(value).strip()]
        if not values:
            raise forms.ValidationError('Add at least one instruction step.')
        return values


class RefundAdminForm(forms.ModelForm):
    class Meta:
        model = Refund
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        payment_field = self.fields.get('payment')
        if payment_field is None:
            return
        eligible_payments = payment_field.queryset.filter(
            status__in=('succeeded', 'partially_refunded'),
        )
        if self.instance.pk and self.instance.payment_id:
            eligible_payments = eligible_payments | payment_field.queryset.filter(
                pk=self.instance.payment_id,
            )
        payment_field.queryset = eligible_payments.distinct()

    def clean(self):
        cleaned = super().clean()
        payment = cleaned.get('payment')
        if 'payment' not in self.fields and self.instance.payment_id:
            payment = self.instance.payment
        amount = cleaned.get('amount')
        if payment and amount and not self.instance.pk and payment.status not in {'succeeded', 'partially_refunded'}:
            self.add_error('payment', 'Only successful payments can be refunded.')
        if (
            payment
            and cleaned.get('status', self.instance.status) == 'succeeded'
            and payment.method == 'mpesa'
            and not cleaned.get('provider_reference', self.instance.provider_reference)
        ):
            field = 'provider_reference' if 'provider_reference' in self.fields else None
            self.add_error(field, 'Enter the M-Pesa refund reference before marking this refund successful.')
        return cleaned
