The user has been working on a kitchen design business in Wrocław, Poland.  
 They use Corpus (a parametric CAD program similar to PRO100) for designing. They want to create a system where they   
 can:                                                                                                                  
                                                                                                                       
 1. Define a corpus (cabinet) parametrically with macros                                                               
 2. Generate CSV cutting lists and edge banding lists                                                                  
 3. Generate DXF files with drilling coordinates for hinges, dowels, etc.                                              
                                                                                                                       
 They've been learning about materials (Swiss Krono, Egger), System 32, and CNC outsourcing. Now they want to build a  
 technical system for production data generation.                                                                      
                                                                                                                       
 Let me design a comprehensive solution. This is essentially a parametric furniture specification language + code      
 generator.                                                                                                            
                                                                                                                       
 Key design considerations:                                                                                            
 - YAML for human-readable corpus definitions                                                                          
 - Python for processing (they're in a Python project)                                                                 
 - ezdxf for DXF generation                                                                                            
 - CSV for cutting and edge banding lists                                                                              
 - System 32 drilling patterns as reusable macros                                                                      
 - Blum/Hettich hinge drilling patterns                                                                                
 - Standard cabinet types (base, wall, tall) as templates                                                              
                                                                                                                       
 Let me create a comprehensive architecture proposal with code examples.                                               

 Teraz rozumiem kontekst — masz już wiedzę o materiałach, stylach i Corpusie. Teraz chcesz zbudować system generowania 
 danych produkcyjnych. Oto moja propozycja architektury:                                                               
                                                                                                                       
 ────────────────────────────────────────────────────────────────────────────────                                      
                                                                                                                       
 🏗️ ARCHITEKTURA SYSTEMU: Korpus → CSV + DXF                                                                           
                                                                                                                       
 ### Filozofia                                                                                                         
                                                                                                                       
 ```                                                                                                                   
   ┌─────────────────────────────────────────────────────────────┐                                                     
   │  DEFINICJA KORPUSU (YAML)                                    │                                                    
   │  ─────────────────────                                       │                                                    
   │  Wymiary, materiał, ilość półek, typ zawiasów, uchwyty...   │                                                     
   └─────────────────────┬───────────────────────────────────────┘                                                     
                         │                                                                                             
                         ▼                                                                                             
   ┌─────────────────────────────────────────────────────────────┐                                                     
   │  SILNIK PARAMETRYCZNY (Python)                               │                                                    
   │  ────────────────────────────                                │                                                    
   │  Rozwija makra → oblicza formatki → generuje pozycje otworów │                                                    
   └──────┬──────────────┬──────────────┬─────────────────────────┘                                                    
          │              │              │                                                                              
          ▼              ▼              ▼                                                                              
   ┌──────────┐  ┌──────────┐  ┌──────────────────┐                                                                    
   │ CSV      │  │ CSV      │  │ DXF              │                                                                    
   │ CIĘCIE   │  │ OKLEJANIE│  │ NAWIERTY         │                                                                    
   │          │  │          │  │ (warstwy XY)     │                                                                    
   │ formatka │  │ formatka │  │                  │                                                                    
   │ szer×wys │  │ krawędzie│  │ ○ ∅5  ○ ∅35     │                                                                     
   │ ilość    │  │ materiał │  │ pozycje X,Y      │                                                                    
   └──────────┘  └──────────┘  └──────────────────┘                                                                    
 ```                                                                                                                   
                                                                                                                       
 ### Warstwy systemu                                                                                                   
                                                                                                                       
 ```                                                                                                                   
   kuchnie/                                                                                                            
   ├── corpus_spec/              # Warstwa 1: Definicje                                                                
   │   ├── korpusy/              #   Szablony korpusów (YAML)                                                          
   │   │   ├── dolna_szufladowa.yaml                                                                                   
   │   │   ├── dolna_drzwiowa.yaml                                                                                     
   │   │   ├── gorna_drzwiowa.yaml                                                                                     
   │   │   ├── gorna_klapowa.yaml                                                                                      
   │   │   └── słupek.yaml                                                                                             
   │   ├── makra/                #   Makra nawiertów (YAML)                                                            
   │   │   ├── system32.yaml                                                                                           
   │   │   ├── zawias_blum_35.yaml                                                                                     
   │   │   ├── zawias_hettich_35.yaml                                                                                  
   │   │   ├── prowadnica_blum_metabox.yaml                                                                            
   │   │   ├── prowadnica_blum_tandem.yaml                                                                             
   │   │   ├── uchwyt_rel.yaml                                                                                         
   │   │   ├── zlacze_mimosrodowe.yaml                                                                                 
   │   │   └── kolek_laczacy.yaml                                                                                      
   │   └── materialy/            #   Baza materiałów (YAML)                                                            
   │       ├── swiss_krono.yaml                                                                                        
   │       └── egger.yaml                                                                                              
   │                                                                                                                   
   ├── corpus_engine/            # Warstwa 2: Silnik (Python)                                                          
   │   ├── __init__.py                                                                                                 
   │   ├── models.py             #   Modele danych (Pydantic)                                                          
   │   ├── panel_calculator.py   #   Obliczanie wymiarów formatek                                                      
   │   ├── drill_engine.py       #   Obliczanie pozycji otworów                                                        
   │   ├── csv_generator.py      #   Generowanie CSV                                                                   
   │   ├── dxf_generator.py      #   Generowanie DXF (ezdxf)                                                           
   │   └── macros/               #   Implementacje makr                                                                
   │       ├── system32.py                                                                                             
   │       ├── hinge_blum.py                                                                                           
   │       └── drawer_blum.py                                                                                          
   │                                                                                                                   
   ├── output/                   # Warstwa 3: Wyniki                                                                   
   │   ├── zlecenie_001/                                                                                               
   │   │   ├── ciecie.csv                                                                                              
   │   │   ├── oklejanie.csv                                                                                           
   │   │   ├── nawierty/                                                                                               
   │   │   │   ├── K01-BOK-L.dxf                                                                                       
   │   │   │   ├── K01-BOK-P.dxf                                                                                       
   │   │   │   ├── FRONT-01.dxf                                                                                        
   │   │   │   └── ...                                                                                                 
   │   │   └── raport.txt                                                                                              
   │   └── ...                                                                                                         
   │                                                                                                                   
   └── tests/                    # Warstwa 4: Testy                                                                    
       ├── test_panel_calc.py                                                                                          
       ├── test_drill_positions.py                                                                                     
       └── fixtures/                                                                                                   
 ```                                                                                                                   
                                                                                                                       
 ────────────────────────────────────────────────────────────────────────────────                                      
                                                                                                                       
 WARSTWA 1: Definicja korpusu (YAML)                                                                                   
                                                                                                                       
 ### Przykład: szafka dolna z 2 szufladami                                                                             
                                                                                                                       
 ```yaml                                                                                                               
   # zlecenie_001/szafki/K01.yaml                                                                                      
   korpus:                                                                                                             
     id: "K01"                                                                                                         
     typ: "dolna_szufladowa"                                                                                           
     opis: "Szafka dolna pod zlew, 2 szuflady"                                                                         
                                                                                                                       
     # Wymiary ZEWNĘTRZNE korpusu                                                                                      
     wymiary:                                                                                                          
       szerokosc: 800      # mm                                                                                        
       wysokosc: 720       # mm (standard)                                                                             
       glebokosc: 510      # mm (standard, blat 600mm - 90mm)                                                          
                                                                                                                       
     # Materiały                                                                                                       
     material:                                                                                                         
       korpus: "swiss_krono.U119_VL"    # Beż Jasny Mat                                                                
       plecy: "HDF_3mm"                  # HDF biały 3mm                                                               
       fronty: "swiss_krono.U119_EM"    # Beż Jasny Velvet (MDF)                                                       
                                                                                                                       
     # Grubości płyt                                                                                                   
     grubosci:                                                                                                         
       boki: 18          # mm                                                                                          
       dna: 18           # mm                                                                                          
       polki: 18         # mm                                                                                          
       plecy: 3          # mm (HDF)                                                                                    
       fronty: 18        # mm (MDF)                                                                                    
                                                                                                                       
     # Oklejanie krawędzi (dla korpusu)                                                                                
     oklejanie:                                                                                                        
       typ: "ABS"                                                                                                      
       grubosc: 0.8      # mm                                                                                          
       kolor: "dopasowany_do_materialu"                                                                                
       technologia: "PUR"  # lub "laser"                                                                               
                                                                                                                       
     # Plecy                                                                                                           
     plecy:                                                                                                            
       typ: "wpuszczane_w_nut"   # lub "przybijane"                                                                    
       nut: 8                     # mm głębokości rowka                                                                
                                                                                                                       
     # Elementy wewnętrzne                                                                                             
     wnetrze:                                                                                                          
       # Szuflady                                                                                                      
       szuflady:                                                                                                       
         - id: "S1"                                                                                                    
           typ: "blum_metabox"      # lub "blum_tandem", "blum_legrabox"                                               
           wysokosc: 150            # mm (frontu)                                                                      
           wysokosc_wewnetrzna: 120 # mm (kosza)                                                                       
         - id: "S2"                                                                                                    
           typ: "blum_metabox"                                                                                         
           wysokosc: 300            # mm (frontu)                                                                      
           wysokosc_wewnetrzna: 270 # mm                                                                               
                                                                                                                       
       # Półki (jeśli nie ma szuflad)                                                                                  
       # polki:                                                                                                        
       #   - id: "P1"                                                                                                  
       #     pozycja_od_dolu: 352   # mm                                                                               
                                                                                                                       
     # Fronty                                                                                                          
     fronty:                                                                                                           
       - id: "F1"                                                                                                      
         typ: "szufladowy"                                                                                             
         powiazany: "S1"            # ID szuflady                                                                      
         margines_gora: 3           # mm luka między frontami                                                          
         margines_dol: 3                                                                                               
         margines_lewo: 3                                                                                              
         margines_prawo: 3                                                                                             
       - id: "F2"                                                                                                      
         typ: "szufladowy"                                                                                             
         powiazany: "S2"                                                                                               
         margines_gora: 3                                                                                              
         margines_dol: 3                                                                                               
         margines_lewo: 3                                                                                              
         margines_prawo: 3                                                                                             
                                                                                                                       
     # Uchwyty                                                                                                         
     uchwyty:                                                                                                          
       typ: "relingowy"                                                                                                
       rozstaw: 256                 # mm                                                                               
       pozycja: "srodek_frontu"     # lub "gora", "dol"                                                                
       srednica_otworu: 5           # mm                                                                               
                                                                                                                       
     # Nóżki                                                                                                           
     nozki:                                                                                                            
       wysokosc: 100                # mm                                                                               
       typ: "regulowane"                                                                                               
 ```                                                                                                                   
                                                                                                                       
 ### Przykład: szafka górna z drzwiami                                                                                 
                                                                                                                       
 ```yaml                                                                                                               
   # zlecenie_001/szafki/G01.yaml                                                                                      
   korpus:                                                                                                             
     id: "G01"                                                                                                         
     typ: "gorna_drzwiowa"                                                                                             
     opis: "Szafka wisząca nad zlewem"                                                                                 
                                                                                                                       
     wymiary:                                                                                                          
       szerokosc: 800                                                                                                  
       wysokosc: 720                                                                                                   
       glebokosc: 300               # mm (standard górnych)                                                            
                                                                                                                       
     material:                                                                                                         
       korpus: "swiss_krono.U119_VL"                                                                                   
       plecy: "HDF_3mm"                                                                                                
       fronty: "swiss_krono.U119_EM"                                                                                   
                                                                                                                       
     grubosci:                                                                                                         
       boki: 18                                                                                                        
       dna: 18                                                                                                         
       polki: 18                                                                                                       
       plecy: 3                                                                                                        
       fronty: 18                                                                                                      
                                                                                                                       
     oklejanie:                                                                                                        
       typ: "ABS"                                                                                                      
       grubosc: 0.8                                                                                                    
                                                                                                                       
     plecy:                                                                                                            
       typ: "wpuszczane_w_nut"                                                                                         
       nut: 8                                                                                                          
                                                                                                                       
     wnetrze:                                                                                                          
       polki:                                                                                                          
         - id: "P1"                                                                                                    
           pozycja_od_dolu: 352                                                                                        
         - id: "P2"                 # druga półka jeśli potrzebna                                                      
           pozycja_od_dolu: 544                                                                                        
                                                                                                                       
     fronty:                                                                                                           
       - id: "F1"                                                                                                      
         typ: "drzwiowy_lewy"                                                                                          
         zawias: "blum_clip_35"                                                                                        
         ilosc_zawiasow: 2                                                                                             
         pozycja_pierwszego_zawiasu: 100  # mm od góry                                                                 
                                                                                                                       
       - id: "F2"                                                                                                      
         typ: "drzwiowy_prawy"                                                                                         
         zawias: "blum_clip_35"                                                                                        
         ilosc_zawiasow: 2                                                                                             
         pozycja_pierwszego_zawiasu: 100                                                                               
                                                                                                                       
     uchwyty:                                                                                                          
       typ: "relingowy"                                                                                                
       rozstaw: 256                                                                                                    
       pozycja: "srodek_frontu"                                                                                        
 ```                                                                                                                   
                                                                                                                       
 ────────────────────────────────────────────────────────────────────────────────                                      
                                                                                                                       
 WARSTWA 1: Makra nawiertów (YAML)                                                                                     
                                                                                                                       
 ```yaml                                                                                                               
   # makra/zawias_blum_35.yaml                                                                                         
   macro:                                                                                                              
     id: "zawias_blum_35"                                                                                              
     nazwa: "Zawias puszkowy Blum CLIP top 35mm"                                                                       
     wersja: "1.0"                                                                                                     
                                                                                                                       
     # Otwór pod puszkę                                                                                                
     puszka:                                                                                                           
       srednica: 35           # mm                                                                                     
       glebokosc: 13           # mm                                                                                    
       typ: "frez_forstner"    # narzędzie CNC                                                                         
                                                                                                                       
     # Otwory mocujące (2 warianty do wyboru)                                                                          
     mocowanie:                                                                                                        
       wariant_A:                                                                                                      
         nazwa: "znaczniki_pod                                                                                         
 ```                                