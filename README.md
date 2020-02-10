# blog-builder
Python static site generator for my blog

This is a custom site generator that uses Mako templating and Markdown to convert a directory tree of blog or portfolio entries into a static site. It's a little clunky and needs refactoring, so I can't recommend anyone actually use it, but it works for me!

A TODO here is to make a tiny example site so you can see how things work. 

Site settings are indicated in a configuration file which should be the first argument.
Template files and content tree structures also pointed to in configuration file. Needs more documentation, sorry!

Usage: python3 builder.py config.py
