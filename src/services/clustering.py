"""
Semantic clustering service using OpenAI embeddings.
"""

import numpy as np
from typing import List
from sklearn.cluster import KMeans
from openai import OpenAI
from sqlalchemy.orm import Session
from src.models import Contact
from src.config import config
import logging

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)


def generate_embedding(text: str, model: str = None) -> List[float]:
    """Generate embedding for text."""
    model = model or config.OPENAI_MODEL_EMBEDDING

    response = client.embeddings.create(
        model=model,
        input=text
    )

    return response.data[0].embedding


def generate_embeddings(contacts: List[Contact], db: Session = None) -> np.ndarray:
    """
    Generate embeddings for contacts.

    Args:
        contacts: List of contacts
        db: Optional database session

    Returns:
        NumPy array of embeddings
    """
    embeddings = []

    for contact in contacts:
        # Build text from contact data
        parts = [
            contact.name or "",
            contact.industry or "",
            contact.company or "",
            contact.painpoint or "",
            contact.title or ""
        ]
        text = " ".join([p for p in parts if p])

        # Generate embedding
        embedding = generate_embedding(text)
        embeddings.append(embedding)

        # Save to database if provided
        if db:
            contact.embedding = embedding
            db.add(contact)

    if db:
        db.commit()

    return np.array(embeddings)


def cluster_contacts(
    contacts: List[Contact],
    db: Session = None,
    n_clusters: int = None,
    auto_k: bool = False,
    generate_labels: bool = False
) -> List:
    """
    Cluster contacts by semantic similarity.

    Args:
        contacts: List of contacts
        db: Optional database session
        n_clusters: Number of clusters (if None, auto-detect)
        auto_k: Auto-detect optimal k
        generate_labels: Generate labels for clusters

    Returns:
        List of Cluster objects with contacts
    """
    from dataclasses import dataclass, field

    @dataclass
    class Cluster:
        contacts: List[Contact] = field(default_factory=list)
        label: str = None

    if len(contacts) == 0:
        return []

    if len(contacts) == 1:
        return [Cluster(contacts=contacts, label=contacts[0].industry)]

    # Generate embeddings
    embeddings = generate_embeddings(contacts, db)

    # Determine number of clusters
    if auto_k or n_clusters is None:
        n_clusters = min(3, len(contacts))

    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)

    # Group contacts by cluster
    clusters_dict = {}
    for i, label in enumerate(labels):
        if label not in clusters_dict:
            clusters_dict[label] = []
        clusters_dict[label].append(contacts[i])

    # Create Cluster objects
    clusters = []
    for label, cluster_contacts in clusters_dict.items():
        # Generate cluster label from most common industry
        if generate_labels and cluster_contacts:
            industries = [c.industry for c in cluster_contacts if c.industry]
            if industries:
                from collections import Counter
                most_common = Counter(industries).most_common(1)[0][0]
                cluster_label = most_common
            else:
                cluster_label = f"Cluster {label}"
        else:
            cluster_label = f"Cluster {label}"

        clusters.append(Cluster(contacts=cluster_contacts, label=cluster_label))

    logger.info(f"Created {len(clusters)} clusters from {len(contacts)} contacts")

    return clusters
