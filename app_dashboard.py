import io, re, unicodedata
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Seguimiento de reportes técnicos", page_icon="🚦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#f4f7fb;color:#102448}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#13385f,#102d4c);}
[data-testid="stSidebar"] *{color:white}
.block-container{padding-top:1.2rem;max-width:1600px}
.hero{font-size:2.2rem;font-weight:800;color:#0c2142;margin-bottom:0}
.sub{color:#66758d;margin-top:-5px;margin-bottom:18px}
.card{background:white;border:1px solid #dfe7f1;border-radius:12px;padding:18px 20px;box-shadow:0 2px 8px rgba(20,50,90,.05);height:100%}
.klabel{color:#34445f;font-size:1rem}.kvalue{font-size:2.5rem;font-weight:800;line-height:1.05}.green{color:#219653}.amber{color:#f2a900}.red{color:#d9272e}.navtitle{font-size:1.15rem;font-weight:800;margin-bottom:12px}.rule{border-left:4px solid #2671c8;padding-left:14px;margin:12px 0}.note{background:#e8f2ff;border-radius:8px;padding:10px 14px;color:#29486c;margin:12px 0}
div[data-testid="stDataFrame"]{background:white;border-radius:10px}
.stButton>button,.stDownloadButton>button{border-radius:8px;font-weight:700}
</style>""", unsafe_allow_html=True)

def norm(x):
    if pd.isna(x): return ""
    s=unicodedata.normalize("NFKD",str(x)).encode("ascii","ignore").decode().lower().strip()
    return re.sub(r"\s+"," ",s)

@st.cache_data(show_spinner=False)
def load_book(data):
    xls=pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
    raw=pd.read_excel(xls,"Report",header=None)
    header=next(i for i in range(min(20,len(raw))) if {"id","dr status"}.issubset({norm(v) for v in raw.iloc[i]}))
    d=pd.read_excel(xls,"Report",header=header)
    z=pd.read_excel(xls,"Zonas")
    d.columns=[str(c).strip() for c in d.columns]; z.columns=[str(c).strip() for c in z.columns]
    d=d[d["ID"].notna()].copy()
    d["Created date"]=pd.to_datetime(d["Created date"],errors="coerce",dayfirst=True)
    z["_key"]=z["Sucursal"].map(norm)
    z["Zona"]=z["Zona"].astype(str).str.replace("Zona ","",regex=False).str.strip().str.title()
    z=z[z["Zona"].isin(["Norte","Centro","Sur"])]
    zone_map=z.drop_duplicates("_key").set_index("_key")["Zona"].to_dict()
    aliases={"cws stracon copiapo":"copiapo","cws pozo almonte iquique":"iquique","cws atacama minerales copiapo":"copiapo"}
    loc=d["Dealer_Location"].map(norm).replace(aliases)
    d["Zona"]=loc.map(zone_map).fillna("Sin asignar")
    assigned=d["Assigned to id"].notna() & d["Assigned to id"].astype(str).str.strip().ne("")
    d["Asignado"]=assigned
    d["Días"]=((pd.Timestamp(date.today())-d["Created date"].dt.normalize()).dt.days).clip(lower=0)
    d["Gestión pendiente"]="Fuera de semáforo"
    workshop=d["DR Status"].isin(["New","Open"]) & ~assigned
    d.loc[workshop,"Gestión pendiente"]="Asignar responsable"
    waiting=d["DR Status"].eq("Waiting")
    d.loc[waiting,"Gestión pendiente"]="Responder al concesionario"
    d["Semáforo"]="No aplica"
    d.loc[workshop & d["Días"].le(4),"Semáforo"]="🟢 En plazo"
    d.loc[workshop & d["Días"].between(5,6),"Semáforo"]="🟡 Por vencer"
    d.loc[workshop & d["Días"].ge(7),"Semáforo"]="🔴 Antiguo"
    d.loc[waiting,"Semáforo"]="⚪ Pendiente validar"
    return d

st.sidebar.markdown("<div class='navtitle'>📊 SEGUIMIENTO DAT</div>",unsafe_allow_html=True)
page=st.sidebar.radio("Navegación",["Resumen","Casos","Zonas","Histórico semanal","Configuración"],label_visibility="collapsed")
upload=st.sidebar.file_uploader("Cargar Excel semanal",type=["xlsx"])
if upload: data=upload.getvalue(); source="Archivo cargado"
else:
    try: data=open("Base.xlsx","rb").read(); source="Base.xlsx incluido"
    except FileNotFoundError: st.info("Cargue el Excel semanal para comenzar."); st.stop()
try: df=load_book(data)
except Exception as e: st.error(f"No se pudo leer el archivo: {e}"); st.stop()
st.sidebar.caption(source)
st.sidebar.markdown("---")
st.sidebar.caption("Actualización semanal cada lunes")

st.markdown("<div class='hero'>Seguimiento de reportes técnicos</div>",unsafe_allow_html=True)
st.markdown("<div class='sub'>Dashboard operativo · Norte, Centro y Sur · Antiguo desde 7 días</div>",unsafe_allow_html=True)

zones=st.multiselect("Zona",["Norte","Centro","Sur","Sin asignar"],default=["Norte","Centro","Sur"])
status_options=sorted(df["DR Status"].dropna().astype(str).unique())
statuses=st.multiselect("Estado",status_options,default=status_options)
f=df[df["Zona"].isin(zones)&df["DR Status"].isin(statuses)].copy()

def download_button(frame,name="seguimiento_filtrado.csv"):
    st.download_button("⬇ Exportar",frame.to_csv(index=False).encode("utf-8-sig"),name,"text/csv")

if page=="Resumen":
    eligible=f[f["Gestión pendiente"].eq("Asignar responsable")]
    vals={"total":len(eligible),"green":eligible["Semáforo"].str.contains("En plazo").sum(),"amber":eligible["Semáforo"].str.contains("Por vencer").sum(),"red":eligible["Semáforo"].str.contains("Antiguo").sum()}
    cols=st.columns(4)
    cards=[("Pendientes evaluados",vals["total"],"#244466"),("En plazo · 0–4 días",vals["green"],"#219653"),("Por vencer · 5–6 días",vals["amber"],"#f2a900"),("Antiguos · ≥7 días",vals["red"],"#d9272e")]
    for c,(label,value,color) in zip(cols,cards):
        c.markdown(f"<div class='card'><div class='klabel'>{label}</div><div class='kvalue' style='color:{color}'>{value}</div></div>",unsafe_allow_html=True)
    st.markdown("<div class='note'>ℹ️ Alerta previa: días 5–6. Antiguo desde los 7 días. Waiting se activa cuando exista una fecha válida de respuesta de fábrica.</div>",unsafe_allow_html=True)
    left,right=st.columns([1.15,1])
    with left:
        st.subheader("Semáforo por zona")
        tab=pd.crosstab(eligible["Zona"],eligible["Semáforo"]).reindex(["Norte","Centro","Sur"],fill_value=0)
        ren={c:c.replace("🟢 ","").replace("🟡 ","").replace("🔴 ","") for c in tab.columns}; tab=tab.rename(columns=ren)
        tab=tab.reindex(columns=["En plazo","Por vencer","Antiguo"],fill_value=0); tab["Total"]=tab.sum(axis=1)
        st.dataframe(tab,use_container_width=True)
    with right:
        st.subheader("Reglas de seguimiento")
        st.markdown("<div class='card'><div class='rule'><b>1. Taller · Sin asignar</b><br>Contar desde la fecha del reporte mientras no tenga responsable. Antiguo a los 7 días.</div><div class='rule'><b>2. Waiting · Respuesta pendiente</b><br>Contar desde la respuesta de fábrica mientras siga pendiente responder al concesionario. Antiguo a los 7 días.</div><small>No usar cualquier actualización como respuesta. Closed queda excluido.</small></div>",unsafe_allow_html=True)
    st.subheader("Casos que requieren atención")
    att=f[f["Semáforo"].isin(["🔴 Antiguo","🟡 Por vencer","⚪ Pendiente validar"])].sort_values("Días",ascending=False)
    cols_show=["ID","Zona","DR Status","Dealer_Location","Gestión pendiente","Días","Semáforo"]
    st.dataframe(att[cols_show],use_container_width=True,hide_index=True)
    download_button(att[cols_show])

elif page=="Casos":
    st.subheader("Detalle de casos")
    search=st.text_input("Buscar ID, sucursal o responsable")
    detail=f.copy()
    if search:
        mask=detail.astype(str).apply(lambda c:c.str.contains(search,case=False,na=False)).any(axis=1); detail=detail[mask]
    cols=[c for c in ["ID","Zona","DR Status","Dealer_Location","Assigned to id","Created date","Días","Gestión pendiente","Semáforo"] if c in detail]
    st.dataframe(detail[cols].sort_values("Created date",ascending=False),use_container_width=True,hide_index=True)
    download_button(detail[cols],"casos_filtrados.csv")

elif page=="Zonas":
    st.subheader("Estados por zona")
    q=f.groupby(["Zona","DR Status"]).size().reset_index(name="Casos")
    fig=px.bar(q,x="Zona",y="Casos",color="DR Status",barmode="stack",category_orders={"Zona":["Norte","Centro","Sur"]})
    fig.update_layout(plot_bgcolor="white",paper_bgcolor="white",legend_title="Estado")
    st.plotly_chart(fig,use_container_width=True)
    matrix=pd.crosstab(f["Zona"],f["DR Status"]); matrix["Total"]=matrix.sum(axis=1)
    st.dataframe(matrix,use_container_width=True)

elif page=="Histórico semanal":
    st.subheader("Histórico semanal")
    st.info("Esta base es una fotografía actual. Para mostrar evolución, guarde un corte cada lunes. La aplicación no inventa semanas faltantes.")
    st.markdown("**Estructura sugerida:** Base_2025-12-01.xlsx, Base_2025-12-08.xlsx, etc.")

else:
    st.subheader("Configuración y calidad de datos")
    unm=df[df["Zona"].eq("Sin asignar")]["Dealer_Location"].fillna("(vacío)").value_counts().rename_axis("Sucursal").reset_index(name="Casos")
    st.write("Sucursales sin zona inequívoca")
    st.dataframe(unm,use_container_width=True,hide_index=True)
    st.warning(f"{(df['DR Status']=='Waiting').sum()} casos Waiting están pendientes de validar porque el archivo no contiene una fecha inequívoca de respuesta de fábrica.")
