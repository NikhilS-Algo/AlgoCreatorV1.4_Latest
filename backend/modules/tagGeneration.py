import spacy
import re
import spacy.cli

# Ensure the model is downloaded
spacy.cli.download("en_core_web_sm")

# Load the spaCy language model ONCE
nlp = spacy.load("en_core_web_sm")

def extract_tags(text):
    """Extracts meaningful tags from the input text using spaCy POS tagging and NER."""
    # nlp = spacy.load("en_core_web_sm")

    
    def is_unwanted_noun(token):
        """Checks if the given token is an unwanted noun."""
        if len(token.text) <= 2:
            return True
        abstract_suffixes = ["ness", "ity", "tion", "ment", "ance", "ence", "ism", "hood", "ship"]
        return any(token.text.lower().endswith(suffix) for suffix in abstract_suffixes)

    def clean_tag(tag):
        """Removes unwanted characters from tags."""
        return re.sub(r'[\(\)\[\]\{\}:;\.\,\n]', '', tag).strip()
    
    def remove_overlapping_tags(tags):
        """Removes overlapping unigrams from bigrams."""
        unigrams = set(tag for tag in tags if len(tag.split()) == 1)
        bigrams = [tag for tag in tags if len(tag.split()) == 2]
        final_tags = []
        for bigram in bigrams:
            word1, word2 = bigram.split()
            if word1 in unigrams and word2 in unigrams:
                unigrams.discard(word1)
                unigrams.discard(word2)
                final_tags.append(bigram)
        final_tags.extend(unigrams)
        return final_tags

    # Process text with spaCy
    doc = nlp(text)

    # Extract POS-based tags (NOUN, PROPN)
    spacy_pos_tags = [token.text for token in doc if token.pos_ in ['NOUN', 'PROPN'] and not is_unwanted_noun(token)]
    
    # Extract Named Entity Recognition (NER) tags
    spacy_ner_tags = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT"]]

    # Process tags to remove stopwords and clean them
    combined_spacy_tags = list(set(spacy_pos_tags + spacy_ner_tags))
    removed_stopwords = [tag for tag in combined_spacy_tags if not nlp.vocab[tag].is_stop]
    cleaned_tags = [clean_tag(tag) for tag in removed_stopwords]

    # Remove overlapping tags
    final_tags = remove_overlapping_tags(cleaned_tags)

    # Filter out unwanted tags (e.g., single letters, emails, links)
    final_tags = [tag for tag in final_tags if len(tag) > 1]
    final_tags = [tag for tag in final_tags if not (tag.endswith(".com") or tag.endswith(".in") or '@' in tag)]

    return final_tags