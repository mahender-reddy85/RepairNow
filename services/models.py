from django.db import models
from django.utils.text import slugify

DEFAULT_SERVICE_CATEGORIES = [
    ('AC Repair', 'fa-snowflake', 'Split and window AC servicing, gas refilling, compressor troubleshooting, and PCB repair.'),
    ('Washing Machine Repair', 'fa-soap', 'Top-load, front-load and semi-automatic drum repairs, drain motor replacement, and vibration fixes.'),
    ('Refrigerator Repair', 'fa-temperature-arrow-down', 'Single and double door cooling issues, thermostat calibration, and gas leak sealing.'),
    ('Electrical Repair', 'fa-bolt', 'Short circuit diagnostics, switchboard installation, MCB tripping fixes, and house rewiring.'),
    ('Mobile Repair', 'fa-mobile-screen-button', 'Screen glass replacement, battery swaps, charging port soldering, and water damage recovery.'),
    ('Computer Repair', 'fa-laptop', 'Laptop hardware fixes, SSD upgrades, OS recovery, motherboard component repair, and thermal repasting.'),
    ('TV Repair', 'fa-tv', 'LED/LCD backlight panel replacements, motherboards, HDMI port replacements, and audio board fixes.'),
    ('Vehicle Repair', 'fa-motorcycle', 'Doorstep two-wheeler and four-wheeler breakdown assistance, brake servicing, and battery jumpstarts.'),
    ('Plumbing', 'fa-faucet-drip', 'Pipe leakage sealing, tap and valve replacements, sanitary fitting repairs, and blockage removal.'),
]


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-wrench', help_text="Font Awesome icon class or keyword")
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['name']

    @classmethod
    def ensure_default_categories(cls):
        created_items = []
        for name, icon, description in DEFAULT_SERVICE_CATEGORIES:
            obj, created = cls.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'description': description, 'is_active': True},
            )
            if created:
                created_items.append(obj)
        return created_items

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
