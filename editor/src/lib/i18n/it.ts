// Italian translations.
// Keys are the English source strings. Only strings that differ from English are listed.
const it: Record<string, string> = {
  // common
  'Cancel': 'Annulla',
  'Close': 'Chiudi',
  'Apply': 'Applica',
  'Reset to defaults': 'Ripristina predefiniti',

  // file
  'New': 'Nuovo',
  'Open': 'Apri',
  'Save': 'Salva',
  'Save as': 'Salva con nome',
  'Preview': 'Anteprima',
  'Page setup': 'Configura pagina',
  'Create new template': 'Crea nuovo template',
  'Open template (Ctrl+O)': 'Apri template (Ctrl+O)',
  'Save template (Ctrl+S)': 'Salva template (Ctrl+S)',
  'Save template as': 'Salva template con nome',

  // edit
  'Undo': 'Annulla',
  'Redo': 'Ripeti',
  'Select all': 'Seleziona tutto',
  'Undo (Ctrl+Z)': 'Annulla (Ctrl+Z)',
  'Redo (Ctrl+Y)': 'Ripeti (Ctrl+Y)',
  'Select all cells (Ctrl+A)': 'Seleziona tutte le celle (Ctrl+A)',

  // cell
  'Add cell': 'Aggiungi cella',
  'Delete cell': 'Cancella cella',
  'Move cell left': 'Muovi cella a sinistra',
  'Move cell right': 'Muovi cella a destra',
  'Copy cells': 'Copia celle',
  'Cut cells': 'Taglia celle',
  'Paste cells': 'Incolla celle',
  'Cell text': 'Testo della cella',
  'Cell properties': 'Proprietà cella',
  'Cell width': 'Larghezza cella',
  'Cell height': 'Altezza cella',
  'Background color': 'Colore sfondo',
  'Word wrap': 'A capo automatico',
  'Auto stretch': 'Adatta altezza cella',
  'Split cell': 'Dividi cella',
  'Merge cells horizontally': 'Unisci celle orizzontalmente',
  'Merge cells vertically': 'Unisci celle verticalmente',
  'Add cell (Ins)': 'Aggiungi cella (Ins)',
  'Delete cell (Del)': 'Cancella cella (Del)',
  'Split cell in half (Ctrl+Ins)': 'Dividi cella a metà (Ctrl+Ins)',
  'Merge cells horizontally (Ctrl+Q)': 'Unisci celle orizzontalmente (Ctrl+Q)',

  // band / row
  'Add row': 'Aggiungi riga',
  'Delete row': 'Cancella riga',
  'Copy rows': 'Copia righe',
  'Cut rows': 'Taglia righe',
  'Paste rows': 'Incolla righe',
  'Move row up': 'Muovi riga su',
  'Move row down': 'Muovi riga giù',
  'Rename row': 'Rinomina riga',
  'Row name (e.g. Header, Band, Footer)...': 'Nome riga (es. Header, Band, Footer)...',
  'Add row (Alt+Ins)': 'Aggiungi riga (Alt+Ins)',
  'Delete row (Alt+Del)': 'Cancella riga (Alt+Del)',
  'Move up (Alt+↑)': 'Muovi su (Alt+↑)',
  'Move down (Alt+↓)': 'Muovi giù (Alt+↓)',
  'Click to select · Double-click to rename': 'Click per selezionare · Doppio click per rinominare',

  // format
  'Font': 'Font',
  'Font color': 'Colore font',
  'Font name': 'Nome font',
  'Font size': 'Dimensione font',
  'Bold': 'Grassetto',
  'Italic': 'Corsivo',
  'Underline': 'Sottolineato',
  'Align left': 'Allinea a sinistra',
  'Align center': 'Allinea al centro',
  'Align right': 'Allinea a destra',
  'Justify': 'Giustificato',
  'Top': 'In alto',
  'Middle': 'Al centro',
  'Bottom': 'In basso',
  'Increase font (Ctrl+])': 'Aumenta dimensione (Ctrl+])',
  'Decrease font (Ctrl+[)': 'Diminuisci dimensione (Ctrl+[)',
  'Bold (Ctrl+B)': 'Grassetto (Ctrl+B)',
  'Italic (Ctrl+I)': 'Corsivo (Ctrl+I)',
  'Underline (Ctrl+U)': 'Sottolineato (Ctrl+U)',
  'Align left (Ctrl+L)': 'Allinea a sinistra (Ctrl+L)',
  'Align center (Ctrl+E)': 'Allinea al centro (Ctrl+E)',
  'Align right (Ctrl+R)': 'Allinea a destra (Ctrl+R)',
  'Align top (Ctrl+T)': 'In alto (Ctrl+T)',
  'Align middle (Ctrl+G)': 'Al centro (Ctrl+G)',
  'Align bottom (Ctrl+M)': 'In basso (Ctrl+M)',

  // border
  'Border color': 'Colore bordo',
  'Border width': 'Larghezza bordo',
  'No border': 'Senza bordo',
  'Left border': 'Bordo sinistro',
  'Right border': 'Bordo destro',
  'Top border': 'Bordo superiore',
  'Bottom border': 'Bordo inferiore',
  'Remove all borders': 'Rimuovi tutti i bordi',
  'Pen width (px)': 'Spessore penna (px)',
  'Pen style': 'Stile penna',
  'Pen color': 'Colore penna',
  'Top border — click to apply pen, click again to remove (Ctrl+3)': 'Bordo superiore — click applica penna, re-click rimuove (Ctrl+3)',
  'Bottom border — click to apply pen, click again to remove (Ctrl+4)': 'Bordo inferiore — click applica penna, re-click rimuove (Ctrl+4)',
  'Left border — click to apply pen, click again to remove (Ctrl+1)': 'Bordo sinistro — click applica penna, re-click rimuove (Ctrl+1)',
  'Right border — click to apply pen, click again to remove (Ctrl+2)': 'Bordo destro — click applica penna, re-click rimuove (Ctrl+2)',
  'Remove all borders (Ctrl+0)': 'Rimuovi tutti i bordi (Ctrl+0)',

  // color picker
  'Other': 'Altro',

  // toolbar labels
  'Colors': 'Colori',
  'Borders': 'Bordi',
  'Align': 'Allineamento',
  'Cell': 'Cella',
  'Structure': 'Struttura',
  'Text': 'Testo',
  'BG': 'Sfondo',
  'transp.': 'trasp.',
  'Text color (mixed)': 'Colore testo (misto)',
  'Background color (mixed)': 'Colore sfondo (misto)',

  // canvas
  'Band': 'Fascia',
  '+ Row': '+ Riga',

  // header
  'Guides': 'Guide',
  'Toggle design guides': 'Mostra/nascondi guide di design',
  'Configuration': 'Configurazione',

  // config menu
  'Load config': 'Carica configurazione',
  'Save config': 'Salva configurazione',

  // page setup
  'Margins': 'Margini',
  'Left': 'Sinistra',
  'Right': 'Destra',
  'Orientation': 'Orientamento',
  'Paper size': 'Dimensione carta',
  'Portrait': 'Verticale',
  'Landscape': 'Orizzontale',
  'Width': 'Larghezza',
  'Height': 'Altezza',

  // units
  'pixels': 'pixel',
  'millimeters': 'millimetri',
  'inches': 'pollici',

  // options
  'Preferences': 'Preferenze',
  'Default font': 'Font predefinito',
  'User variables': 'Variabili utente',
  'Units': 'Unità',
  'Language': 'Lingua',

  // variables
  'Variables': 'Variabili',
  'New variable name': 'Nuova variabile',
  'Add': 'Aggiungi',
  'Delete': 'Cancella',

  // variable reference panel
  'var: lookup / expression': 'lookup / espressione',
  'var: with formatter': 'con formatter',
  'var: chained formatters': 'formatter in catena',
  'var: \\| splits if expr has |': '\\| separa se expr contiene |',
  'var: locale date': 'data locale',
  'var: explicit date format': 'data con formato',
  'var: thousands + 2 decimals': 'migliaia + 2 decimali',
  'var: currency amount': 'importo con valuta',
  'var: uppercase': 'maiuscolo',
  'var: empty if null/zero': 'vuoto se null/zero',
  'var: image proportional': 'immagine proporzionale',
  'var: barcode Code 128': 'barcode Code 128',
  'var: QR code': 'QR code',
  'System': 'Sistema',

  // cell properties dialog
  'Content': 'Contenuto',
  'Type': 'Tipo',
  'Band target': 'Fascia di destinazione',
  'Geometry': 'Geometria',
  'Text rotation': 'Orientamento testo',
  'CSS extra': 'CSS aggiuntivo',
  'Variable reference': 'Riferimento variabili',
  'Cell properties (Alt+Enter)': 'Proprietà cella (Alt+Enter)',

  // messages
  'Invalid file: not an AndRep template.': 'File non valido: non è un template AndRep.',
  'Invalid file: not an AndRep config.': 'File non valido: non è una configurazione AndRep.',
  'Invalid JSON file.': 'File JSON non valido.',
  'Save changes?': 'Salvare le modifiche?',
};

export default it;
