"""Ingestion module for Gmail and email parsing."""

from app.services.ingestion.gmail_reader import GmailReader
from app.services.ingestion.body_parser import BodyParser

__all__ = ['GmailReader', 'BodyParser']
