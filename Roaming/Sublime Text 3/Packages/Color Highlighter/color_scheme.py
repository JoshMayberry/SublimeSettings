"""A color highlighter that uses color scheme scopes to highlight colors."""

import re
import json

import os
from xml.etree import ElementTree

try:
	from . import st_helper
except ValueError:
	import st_helper

try:
	from . import path
	from . import colors
	from . import load_resource
	from .gutter_icons_color_highlighter import GutterIconsColorHighlighter
except ValueError:
	import path
	import colors
	import load_resource
	from gutter_icons_color_highlighter import GutterIconsColorHighlighter

# NOTE: keep in sync with ColorSchemeBuilder._color_scope_template.
CH_COLOR_SCOPE_NAME = "CH_color"

def replaceColorVars(color_scheme_json, raw_text, *, normalize = False):
	for key, value in color_scheme_json["variables"].items():
		if (key in raw_text):
			raw_text = re.sub("var\({}\)".format(key), value, raw_text)

	if (normalize):
		return colors.normalize_hex_color(raw_text)
	return raw_text

def parse_color_scheme(color_scheme, debug):
	"""
	Load, parse, validate and prepare the color scheme.

	Arguments:
	- color_scheme - the color scheme name to process.
	Returns the new color scheme and a ColorSchemeData and a ColorSchemeWriter for input color scheme.
	"""

	color_scheme_content = load_resource.load_resource(color_scheme)
	if (not st_helper.is_st3()):
		color_scheme_content = color_scheme_content.encode("utf-8")

	#Remove trailing commas
	#See: https://stackoverflow.com/questions/23705304/can-json-loads-ignore-trailing-commas/23705538#23705538
	color_scheme_content = re.sub(",\s*}", "}", color_scheme_content)
	color_scheme_content = re.sub(",\s*]", "]", color_scheme_content)

	color_scheme_json = json.loads(color_scheme_content)

	background_color = replaceColorVars(color_scheme_json, color_scheme_json["globals"]["background"], normalize = True)
	existing_colors = _load_colors(color_scheme_json)
	color_scheme_data = ColorSchemeData(background_color, existing_colors)
	color_scheme_writer = ColorSchemeWriter(color_scheme, color_scheme_json, debug)

	return color_scheme, color_scheme_data, color_scheme_writer


class ColorSchemeData(object):  # pylint: disable=too-few-public-methods
	"""Data object with all the data loaded from a color scheme."""

	def __init__(self, background_color, existing_colors):
		"""
		Create a color scheme data.

		Argumets:
		- background_color - the background color of a color scheme.
		- existing_colors - the colors from color highlighter scopes, written to this color scheme.
		"""
		self.background_color = background_color
		self.existing_colors = existing_colors


class ColorSchemeWriter(object):
	"""A class that writes elements to a color scheme."""

	def __init__(self, color_scheme, color_scheme_json, debug):
		"""
		Create a ColorSchemeWriter.

		Arguments:
		- color_scheme - an absolute path to a color scheme.
		- xml_tree - an ElementTree object for the color scheme.
		- scopes_array_element - an Element that represents the dict array in the color scheme XML.
		- debug - whether to enable debug mode.
		"""
		self._color_scheme = color_scheme
		self._color_scheme_json = color_scheme_json
		self._debug = debug

	def add_scopes(self, scopes):
		"""
		Add scopes to the color scheme.

		Arguments:
		- scopes -- an iterable of Elements with scopes to add.
		"""
		raise NotInplementedError()
		self._scopes_array_element.extend(scopes)
		if self._debug:
			packages_path = os.path.dirname(path.packages_path(path.ABSOLUTE))
			print("ColorHighlighter: action=write_color_scheme scheme=%s" % self._color_scheme[len(packages_path) + 1:])

		init_color_scheme_dir()
		self._xml_tree.write(self._color_scheme, encoding="utf-8")
		try:
			os.remove(path.cached_scheme_path(self._color_scheme))
		except FileNotFoundError:
			# No cache -- no problems.
			pass

	def fix_color_scheme_for_gutter_colors(self):  # pylint: disable=invalid-name
		"""Fix color scheme for gutter icons to work properly."""
		raise NotInplementedError()
		for child in self._scopes_array_element:
			if child.tag != "dict":
				continue

			scope = _get_value_child_with_tag(child, "scope", "string")
			if scope is None:
				continue
			# The scheme is already fixed.
			if scope == GutterIconsColorHighlighter.region_scope:
				return

		if self._debug:
			print("ColorHighlighter: action=fix_color_scheme")
		self.add_scopes([ElementTree.fromstring("""
<dict>
	<key>name</key>
	<string>CH_color_scheme_fix</string>
	<key>scope</key>
	<string>%s</string>
	<key>settings</key>
	<dict>
		<key>foreground</key>
		<string>#ffffff</string>
	</dict>
</dict>
""" % GutterIconsColorHighlighter.region_scope)])


def _get_child_by_tag(element, child_tag):
	for child in element:
		if child.tag == child_tag:
			return child
	return None


def _get_value_child_with_tag(element, key, tag):
	for child_index, child in enumerate(element):
		if child.tag == "key" and child.text == key:
			if child_index + 1 < len(element):
				next_child = element[child_index + 1]
				if next_child.tag == tag:
					return next_child
	return None


def _get_array_element(xml):
	dict_element = _get_child_by_tag(xml, "dict")
	if dict_element is None:
		print(2)
		return None

	return _get_value_child_with_tag(dict_element, "settings", "array")


def _get_scheme_settings_element(array_element):
	for child in array_element:
		if child.tag != "dict":
			continue

		settings = _get_value_child_with_tag(child, "settings", "dict")
		if settings is not None:
			scope = _get_value_child_with_tag(settings, "scope", "string")
			if scope is None:
				return settings
	return None


def _load_colors(color_scheme_json):

	existing_colors = []
	for childCatalogue in color_scheme_json["rules"]:
		if ("background" not in childCatalogue):
			continue

		existing_colors.append(replaceColorVars(color_scheme_json, childCatalogue["background"]))

	return existing_colors

def init_color_scheme_dir():
	"""Initialise the directory for color schemes."""
	_create_if_not_exists(path.data_path(path.ABSOLUTE))
	_create_if_not_exists(path.themes_path(path.ABSOLUTE))


def _create_if_not_exists(path_to_create):
	if not os.path.exists(path_to_create):
		os.mkdir(path_to_create)
