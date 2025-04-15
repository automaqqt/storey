import json
import chromadb
from sentence_transformers import SentenceTransformer
import os
import re
import nltk
from nltk.tokenize import sent_tokenize
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download necessary NLTK data (first time only)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

# Load environment variables
load_dotenv('../.env')  # Load environment variables from backend root

# Configuration
SOURCE_JSON_PATH = 'data/german_tales.json'
CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')  # Path to store DB files
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2' # "intfloat/multilingual-e5-large-instruct"# 'paraphrase-multilingual-MiniLM-L12-v2'  # Lighter and faster, or use multilingual models
# Alternatives: 'paraphrase-multilingual-MiniLM-L12-v2' for multilingual support

# Chunking parameters
MAX_CHUNK_SIZE = 600  # Maximum number of characters per chunk
MIN_CHUNK_SIZE = 250  # Minimum chunk size
CHUNK_OVERLAP = 100   # Character overlap between chunks

tale_list = [
    {
        "title": "Rotkäppchen",
        "full_text": """Es war einmal ein kleines süßes Mädchen, das hatte jedermann lieb, der sie nur ansah, am allerliebsten aber ihre Großmutter. Die wusste gar nicht, was sie alles dem Kinde geben sollte. Einmal schenkte sie ihr ein Käppchen von rotem Samt, und weil es ihr so gut stand und sie nichts anderes mehr tragen wollte, hieß sie nur noch Rotkäppchen. Eines Tages sprach die Mutter: „Komm, Rotkäppchen, da hast du ein Stück Kuchen und eine Flasche Wein, bring das der Großmutter hinaus. Sie ist krank und schwach und wird sich daran laben. Mach dich auf, bevor es heiß wird, und wenn du hinauskommst, so geh hübsch sittsam und lauf nicht vom Wege ab, sonst fällst du und zerbrichst das Glas, und die Großmutter hat nichts. Und wenn du in ihre Stube kommst, so vergiss nicht, guten Morgen zu sagen und guck nicht erst in allen Ecken herum!“ – „Ich will schon alles richtig machen“, sagte Rotkäppchen zur Mutter und gab ihr die Hand darauf.

Die Großmutter aber wohnte draußen im Wald, eine halbe Stunde vom Dorf. Als Rotkäppchen in den Wald kam, begegnete ihr der Wolf. Rotkäppchen wusste nicht, was das für ein böses Tier war, und fürchtete sich nicht. „Guten Tag, Rotkäppchen“, sprach er. „Schönen Dank, Wolf!“ – „Wo hinaus so früh, Rotkäppchen?“ – „Zur Großmutter.“ – „Was trägst du unter der Schürze?“ – „Kuchen und Wein. Gestern haben wir gebacken, da soll sich die kranke und schwache Großmutter etwas zugut tun und sich damit stärken.“ – „Rotkäppchen, wo wohnt deine Großmutter?“ – „Noch eine gute Viertelstunde weiter im Wald, unter den drei großen Eichbäumen, da steht ihr Haus, unten sind die Nusshecken, das wirst du ja wissen“, sagte Rotkäppchen.

Der Wolf dachte bei sich: Das junge, zarte Ding ist ein fetter Bissen, der wird noch besser schmecken als die Alte. Du musst es listig anfangen, damit du beide schnappst. Da ging er ein Weilchen neben Rotkäppchen her, dann sprach er: „Rotkäppchen, sieh einmal die schönen Blumen, die ringsumher stehen. Warum guckst du dich nicht um? Ich glaube, du hörst gar nicht, wie die Vöglein so lieblich singen? Du gehst ja für dich hin, als wenn du zur Schule gingst, und ist so lustig draußen im Wald.“ Rotkäppchen schlug die Augen auf, und als sie sah, wie die Sonnenstrahlen durch die Bäume tanzten und alles voll schöner Blumen stand, dachte sie: Wenn ich der Großmutter einen frischen Strauß mitbringe, wird sie sich freuen. Es ist so früh am Tag, dass ich doch zu rechter Zeit ankomme. Sie lief vom Wege ab in den Wald hinein und suchte Blumen. Und wenn sie eine gebrochen hatte, meinte sie, weiter hinaus stünde eine schönere, und lief danach und geriet immer tiefer in den Wald hinein.

Der Wolf aber ging geradewegs zum Haus der Großmutter und klopfte an die Türe. „Wer ist draußen?“ – „Rotkäppchen, das bringt Kuchen und Wein, mach auf!“ – „Drück nur auf die Klinke“, rief die Großmutter, „ich bin zu schwach und kann nicht aufstehen.“ Der Wolf drückte auf die Klinke, die Türe sprang auf, und er ging gerade zum Bett der Großmutter und verschluckte sie. Dann tat er ihre Kleider an, setzte ihre Haube auf, legte sich in ihr Bett und zog die Vorhänge vor.

Rotkäppchen aber war noch bei den Blumen, und als sie so viele gesammelt hatte, dass sie keine mehr tragen konnte, fiel ihr die Großmutter wieder ein. Sie machte sich auf den Weg zu ihr. Sie wunderte sich, dass die Tür offen stand, und als sie in die Stube trat, kam es ihr so seltsam vor, dass sie dachte: Ei, du mein Gott, wie ängstlich wird mir heute zumute, und bin sonst so gerne bei der Großmutter! Sie rief: „Guten Morgen“, bekam aber keine Antwort. Darauf ging sie zum Bett und zog die Vorhänge zurück. Da lag die Großmutter und hatte die Haube tief ins Gesicht gesetzt und sah so wunderlich aus. „Ei, Großmutter, was hast du für große Ohren!“ – „Dass ich dich besser hören kann!“ – „Ei, Großmutter, was hast du für große Augen!“ – „Dass ich dich besser sehen kann!“ – „Ei, Großmutter, was hast du für große Hände!“ – „Dass ich dich besser packen kann!“ – „Aber Großmutter, was hast du für ein entsetzlich großes Maul!“ – „Dass ich dich besser fressen kann!“ Kaum hatte der Wolf das gesagt, so tat er einen Satz aus dem Bett und verschlang das arme Rotkäppchen.

Als der Wolf seinen Appetit gestillt hatte, legte er sich wieder ins Bett, schlief ein und fing an, überlaut zu schnarchen. Ein Jäger kam am Haus vorbei und dachte: Wie die alte Frau schnarcht! Du musst doch sehen, ob ihr etwas fehlt. Er trat ein und sah den Wolf im Bett liegen. „Finde ich dich hier, du alter Sünder“, sagte er, „ich habe dich lange gesucht.“ Er wollte seine Büchse anlegen, doch dann fiel ihm ein, die Großmutter könnte noch leben. Er schoss nicht, sondern nahm eine Schere und fing an, dem schlafenden Wolf den Bauch aufzuschneiden. Nach ein paar Schnitten sah er das rote Käppchen leuchten, noch ein paar, da sprang das Mädchen heraus und rief: „Ach, wie war ich erschrocken, wie war’s so dunkel in dem Wolf seinem Leib!“ Dann kam auch die Großmutter lebendig heraus und konnte kaum atmen. Rotkäppchen holte schnell große Steine, damit füllten sie dem Wolf den Bauch. Als er aufwachte und fortspringen wollte, waren die Steine so schwer, dass er tot zusammenbrach.

Da waren alle drei vergnügt. Der Jäger zog dem Wolf den Pelz ab und ging heim, die Großmutter aß den Kuchen und trank den Wein, den Rotkäppchen gebracht hatte, und erholte sich. Rotkäppchen aber dachte: Du willst dein Lebtag nicht wieder allein vom Wege ab in den Wald laufen, wenn dir’s die Mutter verboten hat.

Es wird auch erzählt, dass, als Rotkäppchen der Großmutter wieder Gebackenes brachte, ein anderer Wolf sie ansprach und vom Weg abbringen wollte. Rotkäppchen aber hütete sich, ging geradeaus und sagte der Großmutter, dass sie dem Wolf begegnet sei, der böse aus den Augen geschaut habe. „Wenn’s nicht auf offener Straße gewesen wäre, hätte er mich gefressen.“ – „Komm“, sagte die Großmutter, „wir wollen die Tür verschließen, dass er nicht hereinkann.“ Bald danach klopfte der Wolf an und rief: „Mach auf, Großmutter, ich bin das Rotkäppchen, ich bring dir Gebackenes.“ Doch sie schwiegen und öffneten nicht. Da schlich der Graukopf ums Haus, sprang aufs Dach und wollte warten, bis Rotkäppchen abends heimkehrte, um es in der Dunkelheit zu fressen. Doch die Großmutter merkte, was er vorhatte. Vor dem Haus stand ein großer Steintrog. Sie sprach: „Nimm den Eimer, Rotkäppchen, gestern habe ich Würste gekocht, da trag das Wasser, worin sie gekocht wurden, in den Trog!“ Rotkäppchen trug so lange, bis der Trog ganz voll war. Der Duft stieg dem Wolf in die Nase. Er schnupperte, guckte hinab und machte den Hals so lang, dass er abrutschte, in den Trog fiel und ertrank. Rotkäppchen aber ging fröhlich nach Hause, und von nun an tat ihm niemand mehr etwas zuleide.""",
        "original_summary": """Rotkäppchen ist ein klassisches deutsches Volksmärchen, das von den Brüdern Grimm in ihrer Sammlung Kinder- und Hausmärchen (1812) veröffentlicht wurde. Es handelt von einem jungen Mädchen, das aufgrund ihrer auffälligen roten Kappe allgemein nur "Rotkäppchen" genannt wird.

Eines Tages bittet Rotkäppchens Mutter sie, der kranken Großmutter einen Korb mit Kuchen und Wein zu bringen. Die Großmutter lebt allein in einem Haus tief im Wald. Vor dem Aufbruch mahnt die Mutter das Mädchen eindringlich, nicht vom Weg abzuweichen und mit niemandem zu sprechen.

Auf dem Weg durch den Wald begegnet Rotkäppchen einem Wolf. Sie ist freundlich und arglos und beginnt ein Gespräch mit ihm, obwohl sie die Warnung ihrer Mutter kennt. Der Wolf gibt sich harmlos und erfährt so, wohin sie unterwegs ist. Dann schmiedet er einen Plan: Er schlägt vor, dass Rotkäppchen einige Blumen pflückt, um ihrer Großmutter eine Freude zu machen. Während sie damit beschäftigt ist, eilt der Wolf heimlich zum Haus der Großmutter, verschlingt die alte Frau und verkleidet sich mit ihrer Kleidung, um sich in ihr Bett zu legen.

Als Rotkäppchen schließlich im Haus der Großmutter ankommt, wundert sie sich über deren Aussehen. In einem berühmten Dialog fragt sie: „Großmutter, warum hast du so große Ohren?" – „Damit ich dich besser hören kann." So geht es weiter mit Augen, Händen und schließlich dem Maul: „Damit ich dich besser fressen kann!" In diesem Moment springt der Wolf auf und verschlingt auch Rotkäppchen.

Zum Glück hört ein Jäger, der gerade durch den Wald streift, das laute Schnarchen des Wolfs. Er betritt das Haus, erkennt die Situation und schneidet dem Wolf den Bauch auf. Großmutter und Rotkäppchen kommen unversehrt wieder heraus. Um sicherzugehen, dass der Wolf keine weiteren Untaten begeht, füllen sie seinen Bauch mit schweren Steinen. Als der Wolf aufwacht und fliehen will, stürzt er unter dem Gewicht der Steine tot zu Boden.

Die Geschichte endet mit der Lehre, dass man auf die Worte der Eltern hören, nicht vom rechten Weg abkommen und keine Gespräche mit Fremden führen sollte. In späteren Versionen geht Rotkäppchen ein zweites Mal zur Großmutter, trifft wieder einen Wolf, bleibt diesmal aber wachsam und wird nicht getäuscht – ein Hinweis auf die moralische Entwicklung der Figur.

Wichtige Motive und Symbole:

Der Wald steht für das Unbekannte, Gefährliche, aber auch für eine Art Prüfungsraum des Erwachsenwerdens.

Der Wolf symbolisiert Gefahr, Verführung und Täuschung – oft interpretiert als Warnung vor fremden Männern.

Rotkäppchens Kappe gilt als Symbol für kindliche Unschuld, aber auch als Markenzeichen für ihre Rolle im Märchen.

Der Jäger verkörpert Ordnung, Sicherheit und Wiederherstellung der Gerechtigkeit.

Strukturell folgt die Geschichte einer klassischen Märchenform mit Einleitung, moralischer Prüfung, Konflikt, Rettung und Lehre."""
    }
]

class TaleProcessor:
    """A class to handle the processing of fairy tales for semantic search."""
    
    def __init__(self, embedding_model_name, chroma_db_path):
        """Initialize the processor with model and database paths."""
        self.model_name = embedding_model_name
        self.db_path = chroma_db_path
        self.model = None
        self.client = None
        self.collection = None
    
    def load_model(self):
        """Load the sentence transformer model."""
        logger.info(f"Loading embedding model '{self.model_name}'...")
        self.model = SentenceTransformer(self.model_name)
    
    def setup_database(self, collection_name="german_tales", recreate=False):
        """Set up ChromaDB and get/create collection."""
        logger.info(f"Setting up ChromaDB persistent client at '{self.db_path}'...")
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Get or create the collection
        try:
            if recreate:
                self.client.delete_collection(name=collection_name)
                logger.info(f"Deleted existing collection '{collection_name}'.")
                self.collection = self.client.create_collection(name=collection_name)
                logger.info(f"Created new collection '{collection_name}'.")
            else:
                self.collection = self.client.get_collection(name=collection_name)
                logger.info(f"Using existing collection '{collection_name}'.")
        except Exception as e:
            logger.info(f"Creating new collection '{collection_name}'. Error: {str(e)}")
            self.collection = self.client.create_collection(name=collection_name)
    
    def chunk_text_by_sentences(self, text):
        """
        Chunk text by sentences with controlled size and overlap.
        
        This approach:
        1. Splits text into sentences
        2. Combines sentences into chunks respecting max size
        3. Ensures overlap between chunks for context continuity
        """
        # Clean the text: standardize line breaks, remove extra whitespace
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{2,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Get sentences using NLTK
        sentences = sent_tokenize(text)
        
        if not sentences:
            return []
            
        chunks = []
        current_chunk = []
        current_chunk_size = 0
        
        for sentence in sentences:
            # Add sentence length plus a space
            sentence_size = len(sentence) + 1
            
            # If adding this sentence would exceed max size and we have content, 
            # save the current chunk and start a new one
            if current_chunk_size + sentence_size > MAX_CHUNK_SIZE and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # For overlap, keep some sentences from the end of the previous chunk
                # Find how many sentences to keep for overlap
                overlap_size = 0
                overlap_sentences = []
                
                for s in reversed(current_chunk):
                    if overlap_size + len(s) + 1 <= CHUNK_OVERLAP:
                        overlap_sentences.insert(0, s)
                        overlap_size += len(s) + 1
                    else:
                        break
                
                # Start new chunk with overlap
                current_chunk = overlap_sentences
                current_chunk_size = overlap_size
            
            # Add the current sentence to the chunk
            current_chunk.append(sentence)
            current_chunk_size += sentence_size
        
        # Add the last chunk if it has content and meets minimum size
        if current_chunk and current_chunk_size >= MIN_CHUNK_SIZE:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks
    
    def process_tales(self, tales):
        """Process all tales into chunks and prepare for database insertion."""
        all_chunks = []
        all_metadatas = []
        all_ids = []
        tale_metadata = {}
        
        logger.info("Processing tales...")
        for i, tale in enumerate(tales):
            title = tale.get('title')
            full_text = tale.get('full_text')
            
            if not title or not full_text:
                logger.warning(f"Skipping tale index {i} due to missing title or full_text.")
                continue
            
            logger.info(f"  Processing '{title}'...")
            chunks = self.chunk_text_by_sentences(full_text)
            
            if not chunks:
                logger.warning(f"No text chunks generated for '{title}'. Skipping.")
                continue
            
            # Store metadata about the tale
            tale_metadata[title] = {
                "title": title,
                "chunk_count": len(chunks),
                "original_summary": tale.get('original_summary', "")
            }
            
            # Prepare data for ChromaDB insertion
            for j, chunk in enumerate(chunks):
                chunk_id = f"{title.replace(' ', '_')}_{j:04d}"
                
                # Calculate position markers (beginning, middle, end)
                position = "middle"
                if j == 0:
                    position = "beginning"
                elif j == len(chunks) - 1:
                    position = "end"
                
                all_chunks.append(chunk)
                all_metadatas.append({
                    "tale_title": title,
                    "chunk_index": j,
                    "position": position,
                    "total_chunks": len(chunks)
                })
                all_ids.append(chunk_id)
        
        return all_chunks, all_metadatas, all_ids, tale_metadata
    
    def generate_embeddings(self, chunks):
        """Generate embeddings for all text chunks."""
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        return self.model.encode(chunks, show_progress_bar=True)
    
    def add_to_database(self, ids, embeddings, metadatas, chunks):
        """Add all data to the ChromaDB collection."""
        logger.info("Adding data to ChromaDB...")
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=chunks
        )
    
    def save_metadata(self, tale_metadata, metadata_path):
        """Save tale metadata to a separate file."""
        logger.info(f"Saving tale metadata to {metadata_path}...")
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(tale_metadata, f, ensure_ascii=False, indent=2)
    
    def run(self, tales, metadata_path='./app/services/tale_metadata.json', recreate_collection=False):
        """Run the complete processing pipeline."""
        self.load_model()
        self.setup_database(recreate=recreate_collection)
        
        chunks, metadatas, ids, tale_metadata = self.process_tales(tales)
        
        if not chunks:
            logger.error("No valid chunks found to process. Exiting.")
            return False
        
        embeddings = self.generate_embeddings(chunks)
        self.add_to_database(ids, embeddings, metadatas, chunks)
        self.save_metadata(tale_metadata, metadata_path)
        
        logger.info("------------------------------------------")
        logger.info(f"Preprocessing complete.")
        logger.info(f"Processed {len(tales)} tales.")
        logger.info(f"Added {self.collection.count()} chunks to ChromaDB.")
        logger.info(f"Database stored at: {self.db_path}")
        logger.info(f"Metadata stored at: {metadata_path}")
        logger.info("------------------------------------------")
        
        return True

def add_tale_keywords(tales):
    """
    Extract keywords from tales to enhance search capabilities.
    This helps with both character names and important objects/concepts.
    """
    # Simple but effective keyword extraction - can be enhanced later
    for tale in tales:
        text = tale.get("full_text", "")
        # Extract character names and important objects using regex patterns
        # This is a simplified example - could be expanded with NLP
        character_pattern = r'"([A-Z][a-z]+)"'  # Words in quotes starting with capital letters
        characters = set(re.findall(character_pattern, text))
        tale["keywords"] = list(characters)
    return tales

def main():
    """Main entry point for the script."""
    try:
        # Could load from file instead of using the defined list
        tales = add_tale_keywords(tale_list)
        
        processor = TaleProcessor(
            embedding_model_name=EMBEDDING_MODEL_NAME,
            chroma_db_path=CHROMA_DB_PATH
        )
        
        success = processor.run(
            tales=tales,
            metadata_path='./app/services/tale_metadata.json',
            recreate_collection=True  # Set to False to append to existing collection
        )
        
        if success:
            logger.info("Tale processing completed successfully.")
        else:
            logger.error("Tale processing failed.")
    
    except Exception as e:
        logger.error(f"An error occurred during tale processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()