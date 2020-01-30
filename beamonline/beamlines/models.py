from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel, TabbedInterface, ObjectList
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.core import blocks, hooks

from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock

from colorfield.fields import ColorField


@hooks.register('register_rich_text_features')
def register_features(features):
    features.default_features += ['code','blockquote','superscript','subscript','strikethrough']


class ImageCarouselBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    caption = blocks.TextBlock(required=False)

    class Meta:
        icon = 'image'


class BeamlinePage(Page):
    STATUS_COLORS = (
        ('success', 'Normal Operations'),
        ('warning', 'Maintenance'),
        ('dark', 'Shutdown'),
        ('info', 'Upgrade in Progress'),
    )
    name = models.CharField(max_length=255, blank=True,)
    acronym = models.CharField(max_length=255, blank=True, )
    description = RichTextField(blank=True)
    snippet = RichTextField(blank=True, help_text="To be displayed on other parts of the site.")
    sidebar = RichTextField(blank=True)
    schematic = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='+')
    status = models.CharField(max_length=255, blank=True)
    status_color = ColorField(default='#00FF00')
    gallery = StreamField([
        ('image', blocks.ListBlock(ImageCarouselBlock(), template='beamlines/blocks/carousel.html', icon="image")),
    ], null=True, blank=True)

    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock()),
        ('table', TableBlock()),
        ('image', ImageChooserBlock(icon="image")),
        ('embedded_video', EmbedBlock(icon="media")),
    ])

    content_panels = Page.content_panels + [
        FieldPanel('name', classname="full"),
        FieldPanel('acronym', classname="full"),
        FieldPanel('status', classname="half"),
        FieldPanel('status_color', classname="half"),
        FieldPanel('description', classname="full"),
        FieldPanel('sidebar', classname="full"),
        ImageChooserPanel('schematic'),
    ]

    gallery_panel = [
        StreamFieldPanel('gallery', classname="full"),
    ]

    specs_panel = [
        StreamFieldPanel('body', classname="full"),
    ]
    snippet_panel = [
        FieldPanel('snippet', classname='full'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Content'),
        ObjectList(specs_panel, heading='Specs'),
        ObjectList(snippet_panel, heading='Snippet'),
        ObjectList(gallery_panel, heading='Photo Gallery'),
        ObjectList(Page.promote_panels, heading='Promote'),
        ObjectList(Page.settings_panels, heading='Settings', classname="settings"),
    ])


class UserGuidePage(Page):
    icon = models.CharField(max_length=255, blank=True, )
    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock()),
        ('table', TableBlock()),
        ('image', ImageChooserBlock(icon="image")),
        ('embedded_video', EmbedBlock(icon="media")),
    ])

    content_panels = Page.content_panels + [
        FieldPanel('icon', classname="full"),
        StreamFieldPanel('body', classname="full"),
    ]

    subpage_types = ['UserGuidePage']