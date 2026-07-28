\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{editorialupv}[2016/09/05 Editorial de la Universitat Polit?cnica de Val?ncia]
\LoadClass[10pt]{book}

% ------------------------------------------------------

\RequirePackage{ifthen}

% ------------------------------------------------------

\newboolean{Aquatre}\setboolean{Aquatre}{false}
\newboolean{EBOOKPDF}\setboolean{EBOOKPDF}{false}
\newboolean{TFG}\setboolean{TFG}{false}

\newboolean{MargenesSimetricos}\setboolean{MargenesSimetricos}{true}
\newboolean{Imprimir}\setboolean{Imprimir}{false}
\newboolean{DistanciesEquacions}\setboolean{DistanciesEquacions}{true}

\newboolean{RM}\setboolean{RM}{false}
\newboolean{SF}\setboolean{SF}{false}

\newboolean{valencia}\setboolean{valencia}{false}
\newboolean{castellano}\setboolean{castellano}{false}
\newboolean{english}\setboolean{english}{false}

% ------------------------------------------------------

\DeclareOption{tfg}
    {
    \setboolean{Aquatre}{true}
    \setboolean{TFG}{true}
    }

\DeclareOption{ebookpdf}{
	\setboolean{EBOOKPDF}{true}
	\setboolean{Aquatre}{false}
	\setboolean{TFG}{false}
	\setboolean{Imprimir}{false}
	}

\DeclareOption{imprimir}
    {
    \setboolean{MargenesSimetricos}{false}
    \setboolean{Imprimir}{true}
    }

\DeclareOption{rm}{\setboolean{RM}{true}}
\DeclareOption{sf}{\setboolean{SF}{true}}

\DeclareOption{nomathskip}{\setboolean{DistanciesEquacions}{false}}

\DeclareOption{castellano}{
	\setboolean{castellano}{true}
	\setboolean{valencia}{false}
	\setboolean{english}{false}
}
\DeclareOption{valencia}{
	\setboolean{castellano}{false}
	\setboolean{valencia}{true}
	\setboolean{english}{false}
	}
\DeclareOption{english}{
	\setboolean{castellano}{false}
	\setboolean{valencia}{false}
	\setboolean{english}{true}
	}

\DeclareOption{TFG}{\setboolean{CapitolTFG}{true}}

% ------------------------------------------------------

\DeclareOption*{\ClassWarning{editorialupv}{No podem processar l'opci\'{o}: ?\CurrentOption?}}

% ------------------------------------------------------

\ExecuteOptions{tfg,rm,castellano}
\ProcessOptions\relax

% ------------------------------------------------------
% ------------------------------------------------------
% ------------------------------------------------------

\newcommand{\elTitol}{Título del trabajo de fin de Grado}
\newcommand{\lAlumne}[1]{Nombre y apellidos del alumno}
\newcommand{\elsTutors}[1]{Nombre y apellidos del tutor/a o cotutores}
\newcommand{\laTitulacio}[1]{GRADO EN ...}
\newcommand{\laConvocatoria}[1]{[Indicar mes y año]}

\newcommand{\Titulo}[1]{\renewcommand{\elTitol}[1]{#1}}
\newcommand{\Alumnoa}[1]{\renewcommand{\lAlumne}[1]{#1}}
\newcommand{\Tutores}[1]{\renewcommand{\elsTutors}[1]{#1}}
\newcommand{\Titulacion}[1]{\renewcommand{\laTitulacio}[1]{\MakeUppercase{#1}}}
\newcommand{\Convocatoria}[1]{\renewcommand{\laConvocatoria}[1]{#1}}

% ------------------------------------------------------
% ------------------------------------------------------
% ------------------------------------------------------



\RequirePackage{graphicx}
\RequirePackage{calc}
%\RequirePackage{hyperref}

\ifthenelse{\boolean{EBOOKPDF}}{%
	\title{\elTitol}
	\author{\lAlumne}	
	\date{}
	\renewcommand\maketitle{
	\IfFileExists{./configuraciones/referencias_cruzadas}
		{\input{./configuraciones/referencias_cruzadas}}
		{}  
	\begin{titlepage}%
		\enlargethispage{2cm}
		\let\footnotesize\small
		\let\footnoterule\relax
		\let \footnote \thanks
		\null\vfil
		\begin{center}%
			\vskip -40\p@
			\includegraphics[width=4.5cm]{UPV_Campus_Alcoi_val_HORI}\hfill~
			\vskip 40\p@
			{\fontsize{28}{34}\bfseries\itshape\sffamily\@title\par\\}%
			\vskip 6\p@     
			{\color{red!50!black}\rule{\textwidth}{0.5pt}}
			%\lineskip .75em%
			\vskip 50\p@     
			\small\bfseries\sffamily
			MEMORIA PRESENTADA POR:\\[0ex] \small\bfseries\itshape\sffamily
			\lAlumne\newline\\[2ex] \small\bfseries\sffamily
			TUTOR/A: \\[0ex] \small\mdseries\itshape\sffamily
			\elsTutors\newline\\[0.25cm] \small\sffamily\bfseries
			\fboxsep=9pt
			\fcolorbox{black}{black!20}{\parbox{0.85\textwidth}{\small\centering\laTitulacio}}\\[0.5cm]
			\small\sffamily\underline{\textbf{Convocatoria de defensa}}:\ \itshape\mdseries\laConvocatoria
			\vfil\null
		\end{center}\par
	\end{titlepage}%
	\setcounter{footnote}{0}%
	\global\let\thanks\relax
	\global\let\maketitle\relax
	\global\let\@thanks\@empty
	\global\let\@author\@empty
	\global\let\@date\@empty
	\global\let\@title\@empty
	\global\let\title\relax
	\global\let\author\relax
	\global\let\date\relax
	\global\let\and\relax
}}{}

\ifthenelse{\boolean{Imprimir}}{% Si volem imprimir, es genera la portada
	\title{\elTitol}
	\author{\lAlumne}	
	\date{}
	\renewcommand\maketitle{
	\IfFileExists{./configuraciones/referencias_cruzadas}
		{\input{./configuraciones/referencias_cruzadas}}
		{}  
	\begin{titlepage}%
		\enlargethispage{2cm}
		\let\footnotesize\small
		\let\footnoterule\relax
		\let \footnote \thanks
		\null\vfil
		\begin{center}%
			\vskip -75\p@
			\includegraphics[width=6cm]{UPV_Campus_Alcoi_val_HORI}\hfill~
			\vskip 110\p@
			{\fontsize{28}{36}\bfseries\itshape\sffamily\elTitol\par\\}%
			\vskip 6\p@     
			{\color{red!50!black}\rule{\textwidth}{0.5pt}}
			%\lineskip .75em%
			\vskip 100\p@ 
			\Large\bfseries\sffamily   
		    MEMORIA PRESENTADA POR:\\[1ex] \Large\bfseries\itshape\sffamily
			\lAlumne\newline\\[4ex] \large\bfseries\sffamily
			TUTOR/A: \\[1ex] \large\mdseries\itshape\sffamily
			\elsTutors\newline\\[5ex] \Large\sffamily\bfseries
			\fboxsep=9pt
			\fcolorbox{black}{black!20}{\parbox{0.8\textwidth}{\centering\laTitulacio}}\\[1.0cm]
			\sffamily\underline{\textbf{Convocatoria de defensa}}:\ \itshape\mdseries\laConvocatoria
			\vfil\null
		\end{center}\par
	\end{titlepage}%
	\setcounter{footnote}{0}%
	\global\let\thanks\relax
	\global\let\maketitle\relax
	\global\let\@thanks\@empty
	\global\let\@author\@empty
	\global\let\@date\@empty
	\global\let\@title\@empty
	\global\let\title\relax
	\global\let\author\relax
	\global\let\date\relax
	\global\let\and\relax
    }}
    { % Si no volem imprimir, no es genera la portada per pujar el TFG a Ebrón
    \title{\elTitol}
	\author{\lAlumne}	
	\date{}
	\renewcommand\maketitle{
	\IfFileExists{./configuraciones/referencias_cruzadas}
		{\input{./configuraciones/referencias_cruzadas}}
		{}  
	}}

% ---------------------------------------------------------------------
% Tipus de lletra

\ifAquatre
	\renewcommand{\normalsize}{\fontsize{12pt}{14.5pt}\selectfont}
\fi

\ifEBOOKPDF
	\renewcommand{\familydefault}{\rmdefault}
	\renewcommand{\normalsize}{\fontsize{12pt}{14pt}\selectfont}
\fi

% ---------------------------------------------------------------------

\ifSF
	\renewcommand{\familydefault}{\sfdefault}
\else
	\renewcommand{\familydefault}{\rmdefault}
\fi
	

% ---------------------------------------------------------------------
% Format de pàgina

\RequirePackage{geometry}

\ifEBOOKPDF
	
	\geometry{
		twoside = false,
		body={4.75in,6.6in},
		hmarginratio=1:1,
		includeheadfoot,
%		paperwidth = 5.5in,
%		paperheight = 7.5in,
		paperheight=7.60606060in,
   		paperwidth=5.8181818in,
   		vmargin={0cm},
   		headsep = 1.25cm,	
		footnotesep = 0.65cm,
		}

\else\ifAquatre
	
    \ifMargenesSimetricos
	
		\geometry{ 
			a4paper, twoside = false,   % A4 a una cara
			hmargin = {2.5cm, 2.5cm}, 	% {Izquierdo, Derecho}
			vmargin = {1.25cm, 1.25cm}, % {Superior, Inferior} 
			includehead, includefoot, 	% Incluyendo encabezado y pie
			headsep = 1.0cm,          	% Separación entre el encabezado y el texto
			footskip = 1.5cm,        	% Separación entre el texto y el pie
			headheight = 15pt
			}

	\else
	
		\geometry{ 
			a4paper, twoside,         	% A4 a doble cara
			hmargin = {3.0cm, 2.25cm}, 	% {Izquierdo, Derecho}
			vmargin = {1.25cm, 1.25cm}, % {Superior, Inferior} 
			includehead, includefoot, 	% Incluyendo encabezado y pie
			headsep = 1.0cm,          	% Separación entre el encabezado y el texto
			footskip = 1.5cm,        	% Separación entre el texto y el pie
			headheight = 15pt
			}

    \fi

\fi\fi


% ---------------------------------------------------------------------
% Capçaleres i peus de pàgina

\RequirePackage{fancyhdr}
\pagestyle{fancy}

\renewcommand{\chaptermark}[1]{\markboth{\thechapter.\ #1}{}}
\renewcommand{\sectionmark}[1]{\markright{\thesection\ #1}{}}

\fancyhead{} % Esborra la configuraci? de la cap?alera
\fancyfoot{} % Esborra la configuraci? del peu


\newlength{\myevenheadlinehoffset}
\newlength{\myevenheadtexthoffset}
\newlength{\myoddheadlinewidth}
\newlength{\myevenheadlinewidth}

\setlength{\myevenheadlinehoffset}{0.0cm}
\setlength{\myevenheadtexthoffset}{0.0cm}
\setlength{\myoddheadlinewidth}{\textwidth}
\setlength{\myevenheadlinewidth}{\textwidth}

\newlength{\myevenfootlinehoffset}
\newlength{\myoddfootlinehoffset}
\newlength{\myfootlinewidth}

\setlength{\myevenfootlinehoffset}{0cm}
\setlength{\myoddfootlinehoffset}{\textwidth}
\setlength{\myfootlinewidth}{1cm}


\ifEBOOKPDF

	\newlength{\hMargins}
	\setlength{\hMargins}{\paperwidth-\textwidth}
	\newlength{\hMargin}
	\setlength{\hMargin}{0.5\hMargins}
	\newlength{\posPagina}
	\setlength{\posPagina}{\textwidth + 0.5\hMargin}

	\RequirePackage{lastpage}
	\RequirePackage{xcolor}
	\RequirePackage{tikz}
	
	\definecolor{grisUPV}{HTML}{313233}
	\definecolor{grisCLARET}{HTML}{EEEEEE}
	
	\renewcommand{\chaptermark}[1]{\markboth{\@chapapp\ \thechapter.\ #1}{}}

	\fancyhf{} % 
	\fancyhead[L]{%
		\begin{tikzpicture}[overlay]
			\draw[fill=grisUPV] (-\hMargin,2ex) rectangle ++(\paperwidth,-1.0cm);
			\node[right] (leftMark) at (-0.75\hMargin,0) {\color{grisCLARET}\sffamily\mdseries\scriptsize\leftmark};
			\node[right] (rightMark) at (-0.5\hMargin,-2ex) {\color{grisCLARET}\sffamily\mdseries\scriptsize\rightmark};
			\node[] (thePage) at (\posPagina,-1ex) {\color{grisCLARET}\sffamily\small\thepage/\pageref*{LastPage}};
		\end{tikzpicture}
		}

	\fancypagestyle{plain}{% 
	\fancyhf{} % clear all header and footer fields 
	\fancyhead[L]{%
		\begin{tikzpicture}[overlay]
			\draw[fill=grisUPV] (-\hMargin,2ex) rectangle ++(\paperwidth,-1.0cm);
			\node[] (thePage) at (\posPagina,-1ex) {\color{grisCLARET}\sffamily\small\thepage/\pageref*{LastPage}};
		\end{tikzpicture}
		}}
	
	\renewcommand{\headrulewidth}{0.0pt}
	\renewcommand{\footrulewidth}{0.0pt}
	
	\renewcommand{\frontmatter}{}
	\renewcommand{\mainmatter}{}
	
\else\ifAquatre

    \ifMargenesSimetricos

    	\fancyhead[L]{\sffamily\small\upshape\mdseries\leftmark}
    	\fancyhead[R]{\sffamily\small\upshape\mdseries\thepage}
    
    	\renewcommand{\headrulewidth}{0.25pt}
    	\renewcommand{\footrulewidth}{0.00pt}

    \else
    
    	\fancyhead[LE]{\small\itshape\nouppercase\leftmark}
    	\fancyhead[RO]{\small\itshape\nouppercase\rightmark}
    
    	\fancyfoot[LE,RO]{\thepage}
    
    	\renewcommand{\headrulewidth}{0.25pt}
    	\renewcommand{\footrulewidth}{0.25pt}
	
	\fi

\fi\fi

% ---------------------------------------------------------------------
% Format de paràgraf y maquetació

\ifAquatre

	\setlength{\parskip}{3ex}
	\setlength{\parindent}{0pt}

\else

	\setlength{\parskip}{2ex}
	\setlength{\parindent}{0pt}

\fi

\linespread{1.0}

\setlength{\widowpenalty}{10000pt}
\setlength{\clubpenalty}{10000pt}

\raggedbottom

% ---------------------------------------------------------------------
% Mojora los t?tulos de las figuras y tablas

\RequirePackage{caption}
\renewcommand{\captionlabelfont}{\bfseries\small}
\renewcommand{\captionfont}{\small}

% ------------------------------------------------------------------------
% Formato de las secciones

\RequirePackage[
	raggedright,
	compact,
	nobottomtitles*, % Evita que queden títols solts al final de la pàgina
	clearempty, % Modifica \cleardoublepage per a que els fulls parells buides siguen blanques
	]{titlesec}

% ------------------------------------------------------------------------

\titleformat{\part}
	[display]
	{\thispagestyle{empty}\filcenter
	\tolerance=10000\hyphenpenalty=10000}
	{\fontsize{18}{20}\bfseries\partname\enspace\thepart}
	{1pc}
	{\fontsize{24}{30}\bfseries}

% ------------------------------------------------------------------------

\titleformat{\chapter}
	[display]
	{\normalfont\Large\filcenter}
	{\raggedleft\fontsize{18}{20}\bfseries\chaptertitlename\enspace\thechapter}
	{2ex}
	{\raggedleft\fontsize{24}{30}\bfseries}%\usefont{T1}{cmss}{n}{n}\selectfont
	[\vspace{2cm}]


% ------------------------------------------------------------------------

\ifAquatre

	\titleformat{\chapter}
		[hang]
		{\raggedright\tolerance=10000\hyphenpenalty=10000}
		{\fontsize{24}{30}\bfseries\thechapter}
		{1em}
		{\raggedright\fontsize{24}{30}\bfseries}%\usefont{T1}{cmss}{n}{n}\selectfont
		[\vspace{2cm}]
		
	% ------------------------------------------------------------------------
	
	\titleformat{\section}
		[hang]
		{\vspace{2ex}\raggedright\tolerance=10000\hyphenpenalty=10000}
		{\Large\bfseries\thesection}
		{1em}
		{\Large\bfseries}
	
	% ------------------------------------------------------------------------
	
	\titleformat{\subsection}
		[hang]
		{\vspace{1.5ex}\raggedright\tolerance=10000\hyphenpenalty=10000}
		{\large\bfseries\itshape\thesubsection}
		{1em}
		{\large\bfseries\itshape}
		[\vspace{-1ex}]
	

\else\ifEBOOKPDF

	% ------------------------------------------------------------------------
	
	\titleformat{\section}
		[hang]
		{\vspace{2ex}\raggedright\tolerance=10000\hyphenpenalty=10000}
		{\fontsize{13}{15}\bfseries\thesection}
		{1em}
		{\fontsize{15}{15}\bfseries}
	
	% ------------------------------------------------------------------------
	
	\titleformat{\subsection}
		[hang]
		{\vspace{1.5ex}\raggedright\tolerance=10000\hyphenpenalty=10000}
		{\fontsize{12}{14}\bfseries\itshape\thesubsection}
		{1em}
		{\fontsize{12}{14}\bfseries\itshape}
		[\vspace{-1ex}]
	
\fi\fi


% ------------------------------------------------------------------------

\titleformat{\subsubsection}
	[hang]
	{\vspace{2ex}\raggedright\tolerance=10000\hyphenpenalty=10000}
	{\normalsize\itshape\thesubsubsection}
	{1em}
	{\normalsize\itshape}
	[\vspace{-0.75ex}]

% -------------------------------------------------------
% Para controlar la numeración y formato de la tabla de contenidos, lista de figuras y tablas

\setcounter{tocdepth}{1}

\RequirePackage[titles]{tocloft}

\renewcommand{\cftchapaftersnum}{}
\renewcommand{\cftchapfont}{\mdseries}

\renewcommand{\cftsecfont}{\small}
\renewcommand{\cftsecpagefont}{\small}
\renewcommand{\cftsecaftersnum}{}

\renewcommand{\cftfigfont}{\small}
\renewcommand{\cftfigpagefont}{\small}

\renewcommand{\cfttabfont}{\small}
\renewcommand{\cfttabpagefont}{\small}

% ------------------------------------------------------------------------
% ------------------------------------------------------------------------
% ------------------------------------------------------------------------

\RequirePackage{enumitem}
\setlist[1]{partopsep=-1.5ex,parsep=\parskip,itemsep=0\parskip}
\setlist[2]{partopsep=-1.5ex,parsep=\parskip,itemsep=0\parskip}


% ------------------------------------------------------------------------
% ------------------------------------------------------------------------
% ------------------------------------------------------------------------

\RequirePackage{mathtools}

\ifDistanciesEquacions
\AtBeginDocument
	{
	% ---------------------------------------------------
	% Dist?ncies de les equacions al text
	
	% Per a les equacions normals
	\abovedisplayshortskip = -1.0ex plus 0ex minus 0.25ex
	\belowdisplayshortskip = 2.0ex plus 1ex minus 0.0ex
	
	% Per a les equacions en varies l?nies
	\abovedisplayskip = -1.0ex plus 0ex minus 0.25ex
	\belowdisplayskip = 2.0ex plus 1ex minus 0.0ex
	}
\fi

% ------------------------------------------------------------------------
% ------------------------------------------------------------------------
% ------------------------------------------------------------------------
