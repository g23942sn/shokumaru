from django import forms
from .models import Ingredient, HealthCondition

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'quantity', 'expiry_date'] # ユーザーに入力してほしい項目
        widgets = { # 入力欄のデザインを少し整える
            'name': forms.TextInput(attrs={'placeholder': '例：豚バラ肉'}),
            'quantity': forms.TextInput(attrs={'placeholder': '例：200g'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

class HealthConditionForm(forms.ModelForm):
    class Meta:
        model = HealthCondition
        fields = ['condition']
        widgets = {
            'condition': forms.Textarea(attrs={'placeholder': '例：少し疲れ気味、さっぱりしたものが食べたい'}),
        }