import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

const [entrada, destino, modulos, previewDir] = process.argv.slice(2);
const requireRuntime = createRequire(path.join(modulos, 'package.json'));
const {Workbook, SpreadsheetFile} = await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const datos = JSON.parse(await fs.readFile(entrada, 'utf8'));
const analisis = datos.analisis_textual;
if (!analisis) throw new Error('Falta el análisis textual de entrada');
const wb = Workbook.create();
const resumen = wb.worksheets.add('Resumen');
const fuentes = wb.worksheets.add('Videos');
const lectura = datos.lectura_ia ? wb.worksheets.add('Lectura IA') : null;
const azul = '#183153', acento = '#3869B1';
for (const s of [resumen, fuentes, ...(lectura?[lectura]:[])]) {
  s.showGridLines = false;
  s.getRange('A1:P70').format.font = {name:'Arial', size:11, color:'#243247'};
  s.getRange('A1:P70').format.rowHeight = 22;
  s.getRange('A1:P70').format.verticalAlignment = 'center';
}
function titulo(s, celda, texto) {
  s.getRange(celda).values = [[texto]];
  s.getRange(celda).format.font = {name:'Arial',size:16,bold:true,color:azul};
}
function cabecera(s, rango) {
  s.getRange(rango).format = {fill:azul,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:32};
}
function nota(s, rango, texto, alto=38) {
  s.getRange(rango).merge();
  s.getRange(rango).values=[[texto]];
  s.getRange(rango).format={wrapText:true,rowHeight:alto,verticalAlignment:'center',font:{name:'Arial',size:11,color:'#65501E'},fill:'#FFF3D5'};
}
function literal(v) {return typeof v==='string' && v.startsWith('=') ? "'"+v : v;}
function barras(s, rango, tituloGrafico, inicio, fin) {
  const c=s.charts.add('bar',s.getRange(rango));
  c.title=tituloGrafico;
  c.titleTextStyle.fontSize=14;
  c.titleTextStyle.typeface='Arial';
  c.hasLegend=false;
  c.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};
  c.yAxis={numberFormatCode:'#,##0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
  c.series.items[0].fill=acento;
  c.setPosition(inicio,fin);
  return c;
}

resumen.getRange('A1').format.columnWidth=3;
resumen.getRange('B1').format.columnWidth=36;
resumen.getRange('C1').format.columnWidth=18;
resumen.getRange('D1').format.columnWidth=18;
resumen.getRange('E1').format.columnWidth=3;
resumen.getRange('F1:N1').format.columnWidth=11;
titulo(resumen,'B2',`${datos.videos.length} publicaciones observadas · @${datos.usuario_solicitado}`);
nota(resumen,'B4:N4',`Consulta: ${datos.consultado_utc} | Estado: ${datos.estado} | HTTP: ${datos.http ?? 'no registrado en captura de navegador'}`,28);
resumen.getRange('B6:C9').values=[['Cobertura','Cantidad'],['Videos recibidos',datos.videos.length],['Con descripción no vacía',analisis.base_descripciones_no_vacias],['Objetivo solicitado',10]];
cabecera(resumen,'B6:C6');
nota(resumen,'B11:N11',datos.videos.length ? 'Muestra de diez candidatos recientes del listado público. El orden cronológico no está completamente verificado: faltan fechas y hay videos anclados.' : 'TikTok no entregó videos identificables. No hay descripciones para analizar: las barras vacías representan datos ausentes, no rasgos bajos.',46);
resumen.getRange('B13:C13').values=[['Indicador del texto','Videos']];
cabecera(resumen,'B13:C13');
for(let i=0;i<4;i++) {
  const indicador=analisis.indicadores_contenido[i], col=String.fromCharCode(82+i);
  resumen.getRange(`B${14+i}`).values=[[indicador.indicador]];
  resumen.getRange(`C${14+i}`).formulas=[[analisis.base_descripciones_no_vacias?`=COUNTIFS(Videos!${col}7:${col}16,1)`:'=""']];
}
barras(resumen,'B13:C17','Contenido de las descripciones (videos)','F13','N27');
nota(resumen,'B20:D22','Un video puede aparecer en varios indicadores. Son rasgos del texto, no puntuaciones de personalidad.',38);

resumen.getRange('B29:D29').values=[['Video','Visualizaciones','Me gusta']];
cabecera(resumen,'B29:D29');
for(let i=0;i<10;i++) {
  const r=30+i, v=datos.videos[i];
  resumen.getRange(`B${r}:D${r}`).formulas=[[
    `=IF(Videos!A${7+i}="","",Videos!A${7+i})`,
    `=IF(ISNUMBER(Videos!F${7+i}),Videos!F${7+i},"")`,
    `=IF(ISNUMBER(Videos!G${7+i}),Videos!G${7+i},"")`,
  ]];
}
resumen.getRange('C30:D39').setNumberFormat('#,##0');
barras(resumen,'B29:C39','Visualizaciones disponibles por video','F29','N43');
const vistasAbreviadas=datos.videos.filter(v=>v.visualizaciones==null && v.visualizaciones_texto).map(v=>v.visualizaciones_texto);
nota(resumen,'B41:D43',vistasAbreviadas.length?`Se omite del gráfico el conteo abreviado ${vistasAbreviadas.join(', ')}; no equivale a cero. Las barras muestran únicamente conteos exactos recibidos.`:'Los conteos ausentes quedan vacíos; no se sustituyen por cero.',38);

titulo(resumen,'B45','Big Five: lectura orientativa del contenido');
nota(resumen,'B47:N47',lectura?'La IA cita textos en dos dimensiones y declara evidencia insuficiente en las otras. Las barras cuentan videos citados; no miden la personalidad ni son porcentajes.':'Conteo léxico exploratorio, sin puntuaciones de personalidad. Una coincidencia no demuestra un rasgo; la ausencia de palabras tampoco demuestra un nivel bajo.',46);
resumen.getRange('B49:C49').values=[['Dimensión',lectura?'Videos citados':'Descripciones con señal']];
cabecera(resumen,'B49:C49');
resumen.getRange('B49:C49').format.rowHeight=38;
for(let i=0;i<5;i++) {
  const r=50+i, eje=analisis.big_five_textual[i];
  resumen.getRange(`B${r}`).values=[[lectura?datos.lectura_ia.dimensiones[i].dimension:eje.dimension]];
  const col=String.fromCharCode(75+i);
  resumen.getRange(`C${r}`).formulas=[[lectura?`='Lectura IA'!C${7+i}`:analisis.base_descripciones_no_vacias ? `=COUNTIFS(Videos!${col}7:${col}16,">0")` : '=""']];
}
const graficoIA=barras(resumen,'B49:C54',lectura?'Videos citados en la lectura IA (sin puntuaciones)':'Descripciones con señales léxicas por dimensión','F49','N64');
graficoIA.yAxis={numberFormatCode:'0.0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
resumen.getRange('B50:B54').format.wrapText=true;
resumen.getRange('B54:C54').format.rowHeight=38;
nota(resumen,'B57:D59',lectura?'La lectura semántica está en la hoja Lectura IA. No se puede establecer un perfil fiable con esta muestra breve. Cero citas no significa un rasgo bajo.':'No hay una respuesta de IA integrada. El archivo de lectura IA contiene las fuentes para una interpretación semántica separada, con citas y evidencia insuficiente cuando corresponda.',48);

fuentes.getRange('A1').format.columnWidth=14;
fuentes.getRange('B1').format.columnWidth=29;
fuentes.getRange('C1').format.columnWidth=65;
fuentes.getRange('D1').format.columnWidth=24;
fuentes.getRange('E1').format.columnWidth=65;
fuentes.getRange('F1:I1').format.columnWidth=17;
fuentes.getRange('J1:O1').format.columnWidth=19;
fuentes.getRange('P1').format.columnWidth=52;
fuentes.getRange('Q1').format.columnWidth=42;
fuentes.getRange('R1:U1').format.columnWidth=18;
fuentes.getRange('V1').format.columnWidth=24;
fuentes.getRange('Q1:V40').format.font={name:'Arial',size:11,color:'#243247'};
titulo(fuentes,'A2','Fuentes y análisis reproducible');
nota(fuentes,'A4:H4',`Fuente del perfil: ${datos.url_consultada}. Cada URL de video consta en la columna E. Captura UTC: ${datos.consultado_utc}`,40);
const encabezados=['Video','Referencia (ID)','Descripción capturada','Fecha mostrada','URL pública','Visualizaciones exactas','Me gusta','Comentarios','Compartidos','Palabras','Apertura (léxico)','Responsabilidad (léxico)','Extraversión (léxico)','Amabilidad (léxico)','Tono de tensión (léxico)','Coincidencias léxicas','Fuente de descripción','Difusión','Emojis afectivos','Menciones','Humor','Visualizaciones (texto)'];
fuentes.getRange('A6:V6').values=[encabezados]; cabecera(fuentes,'A6:V6');
fuentes.getRange('A6:V6').format.rowHeight=48;
fuentes.freezePanes.freezeRows(6); fuentes.freezePanes.freezeColumns(2);
const ejes=analisis.big_five_textual.map(e=>e.dimension);
for(let i=0;i<datos.videos.length;i++) {
  const v=datos.videos[i], d=analisis.detalle[i];
  const fila=[`Video ${i+1}`,"ID: "+String(v.id_video),literal(v.descripcion),v.fecha_publicacion_texto??v.fecha_utc??null,v.enlace,v.visualizaciones,v.me_gusta,v.comentarios,v.compartidos,d.palabras,...ejes.map(e=>d.descripcion_disponible?Number(d.senales[e].length>0):null),ejes.filter(e=>d.senales[e].length).map(e=>`${e}: ${d.senales[e].join(', ')}`).join(' | '),v.descripcion_fuente??'JSON público de página',...['difusion','afecto','menciones','humor'].map(k=>d.contenido[k])];
  fila.push(v.visualizaciones_texto??null);
  fuentes.getRange(`A${7+i}:V${7+i}`).values=[fila];
}
fuentes.getRange('B7:B16').setNumberFormat('@');
fuentes.getRange('D7:D16').setNumberFormat('@');
fuentes.getRange('F7:O16').setNumberFormat('#,##0');
fuentes.getRange('C7:C16').format.wrapText=true;
fuentes.getRange('P7:P16').format.wrapText=true;
fuentes.getRange('Q7:Q16').format.wrapText=true;
fuentes.getRange('A7:U16').format.rowHeight=76;
if(!datos.videos.length) nota(fuentes,'A7:H7','Sin videos recibidos. No se han creado publicaciones de ejemplo ni descripciones inventadas.',40);
fuentes.getRange('A20:D20').values=[['Dimensión','Vocabulario reproducible','Interpretación','Advertencia']]; cabecera(fuentes,'A20:D20');
for(let i=0;i<5;i++) {
  const eje=analisis.big_five_textual[i];
  fuentes.getRange(`A${21+i}:D${21+i}`).values=[[eje.dimension,analisis.vocabulario[eje.dimension].join(', '),eje.interpretacion,'No equivale a una puntuación Big Five ni evalúa salud mental.']];
}
fuentes.getRange('A21:D25').format.wrapText=true;
fuentes.getRange('A21:D25').format.rowHeight=78;
nota(fuentes,'A28:H29',analisis.metodo,48);
let r=32;
for(const aviso of datos.avisos) nota(fuentes,`A${r}:H${r++}`,aviso,46);

if(lectura) {
  lectura.getRange('A1').format.columnWidth=3;
  lectura.getRange('B1').format.columnWidth=23;
  lectura.getRange('C1').format.columnWidth=14;
  lectura.getRange('D1').format.columnWidth=62;
  lectura.getRange('E1').format.columnWidth=58;
  lectura.getRange('F1').format.columnWidth=44;
  titulo(lectura,'B2','Lectura IA de las descripciones · Big Five');
  nota(lectura,'B4:F4',datos.lectura_ia.metodo,58);
  lectura.getRange('B6:F6').values=[['Dimensión','Videos citados','Lectura del contenido','Explicación alternativa','IDs citados / evidencia']];cabecera(lectura,'B6:F6');
  lectura.getRange('B6:F6').format.rowHeight=44;
  for(let i=0;i<5;i++) {
    const eje=datos.lectura_ia.dimensiones[i], row=7+i;
    lectura.getRange(`B${row}`).values=[[eje.dimension]];
    lectura.getRange(`C${row}`).formulas=[[eje.ids.length?'='+eje.ids.map(id=>`COUNTIFS(Videos!B7:B16,"ID: ${id}")`).join('+'):'=0']];
    lectura.getRange(`D${row}:F${row}`).values=[[eje.interpretacion,eje.alternativa,eje.evidencia+(eje.ids.length?'\n'+eje.ids.join('\n'):'')]];
  }
  lectura.getRange('B7:F11').format.wrapText=true;
  lectura.getRange('B7:F11').format.rowHeight=140;
  lectura.getRange('C7:C11').format.horizontalAlignment='right';
  nota(lectura,'B13:F14',datos.lectura_ia.conclusion,48);
  nota(lectura,'B16:F16','Las citas remiten a los IDs y descripciones de Videos. La IA interpretó solo esos textos: ninguna observación es un diagnóstico ni un nivel psicométrico. Esta lectura es una instantánea; cambiar los textos requiere volver a revisarla.',46);
  lectura.freezePanes.freezeRows(6);
}

wb.recalculate();
const errores=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},maxChars:1800});
console.log(errores.ndjson);
console.log((await wb.inspect({kind:'table',range:'Resumen!B6:C9',include:'values,formulas',tableMaxRows:5,tableMaxCols:2,maxChars:1500})).ndjson);
console.log((await wb.inspect({kind:'table',range:'Resumen!B13:C17',include:'values,formulas',tableMaxRows:5,tableMaxCols:2,maxChars:1500})).ndjson);
console.log((await wb.inspect({kind:'table',range:'Resumen!B49:C54',include:'values,formulas',tableMaxRows:6,tableMaxCols:2,maxChars:1500})).ndjson);
if(previewDir) {
  await fs.mkdir(previewDir,{recursive:true});
  for(const [sheet,range,name] of [['Resumen','B2:N27','resumen'],['Resumen','B29:N43','visualizaciones'],['Resumen','B45:N64','bigfive'],['Videos','A2:H16','fuentes']]) {
    const blob=await wb.render({sheetName:sheet,range,scale:1,format:'png'});
    await fs.writeFile(path.join(previewDir,`${name}.png`),new Uint8Array(await blob.arrayBuffer()));
  }
  if(lectura) {
    const blob=await wb.render({sheetName:'Lectura IA',range:'B2:F16',scale:1,format:'png'});
    await fs.writeFile(path.join(previewDir,'lectura_ia.png'),new Uint8Array(await blob.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(destino),{recursive:true});
try {await fs.access(destino); throw new Error('El archivo destino ya existe; no se sobrescribe');}
catch(error) {if(error.code!=='ENOENT') throw error;}
await (await SpreadsheetFile.exportXlsx(wb)).save(destino);
console.log('Excel exportado:',destino);
