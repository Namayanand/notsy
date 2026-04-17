import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def extract_youtube_transcript(url: str) -> Optional[str]:
    """
    Extract transcript from a YouTube video URL.
    Uses youtube-transcript-api.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from urllib.parse import urlparse, parse_qs

        # Extract video ID from URL
        parsed_url = urlparse(url)
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            if parsed_url.path == '/watch':
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                video_id = parsed_url.path.split('/embed/')[1]
            elif parsed_url.path.startswith('/v/'):
                video_id = parsed_url.path.split('/v/')[1]
            else:
                return None
        elif parsed_url.hostname in ['youtu.be']:
            video_id = parsed_url.path[1:]
        else:
            return None

        if not video_id:
            return None

        # Try to get transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to find English transcript first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            # Fall back to any available transcript
            try:
                transcript = transcript_list.find_transcript(['en-US', 'en-GB'])
            except:
                # Get the first available transcript
                for t in transcript_list:
                    transcript = t
                    break
                else:
                    return None

        transcript_data = transcript.fetch()

        # Combine all text entries
        text = " ".join([entry['text'] for entry in transcript_data])
        return text

    except Exception as e:
        logger.error(f"YouTube transcript extraction failed for {url}: {e}")
        return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url.lower())
        return 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc
    except:
        return False


class YouTubeLoader:
    """Load and process YouTube video content."""

    @staticmethod
    def load(url: str) -> Dict[str, Any]:
        """
        Load YouTube video and extract transcript as chunks.

        Returns:
            List of chunks with text and metadata
        """
        from app.core.document_loader import DocumentLoader

        transcript = extract_youtube_transcript(url)
        if not transcript:
            return {"chunks": [], "error": "Could not extract transcript"}

        # Use the same chunking as document loader
        chunks = DocumentLoader._chunk_text(transcript, 0)

        return {
            "chunks": [{
                "text": chunk["text"],
                "page": 0,
                "chunk_index": chunk["chunk_index"],
                "source": url,
                "type": "youtube"
            } for chunk in chunks],
            "video_url": url
        }
