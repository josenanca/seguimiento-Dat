import io, re, unicodedata
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Seguimiento DAT v2.2", page_icon="📊", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#f4f7fb}[data-testid="stSidebar"]{background:#153b63}[data-testid="stSidebar"] *{color:white}
.block-container{padding-top:1.2rem;max-width:1600px}.hero{font-size:2.1rem;font-weight:800;color:#102448}.sub{color:#66758d;margin-bottom:16px}
.card{background:white;border:1px solid #dfe7f1;border-radius:12px;padding:17px 19px;box-shadow:0 2px 8px rgba(20,50,90,.05)}
.k{font-size:2.25rem;font-weight:800}.muted{color:#65758b}.person{font-size:1.15rem;font-weight:750;color:#153b63}
</style>""", unsafe_allow_html=True)

def norm(x):
    if pd.isna(x): return ""
    s=unicodedata.normalize("NFKD",str(x)).encode("ascii","ignore").decode().lower().strip()
    return re.sub(r"\s+"," ",s)

def find_header(raw, required):
    for i in range(min(20,len(raw))):
        vals={norm(v) for v in raw.iloc[i].tolist()}
        if set(required).issubset(vals): return i
    raise ValueError(f"No se encontró encabezado: {required}")

@st.cache_data(show_spinner=False)
def load_book(data):
    xls=pd.ExcelFile(io.BytesIO(data),engine="openpyxl")
    needed={"Report","Zonas","Responsables"}
    if not needed.issubset(xls.sheet_names): raise ValueError("El Excel debe contener Report, Zonas y Responsables.")
    rr=pd.read_excel(xls,"Report",header=None); rh=find_header(rr,{"id","dr status"})
    zr=pd.read_excel(xls,"Zonas",header=None); zh=find_header(zr,{"sucursal","zona"})
    pr=pd.read_excel(xls,"Responsables",header=None); ph=find_header(pr,{"zona","responsable"})
    d=pd.read_excel(xls,"Report",header=rh); z=pd.read_excel(xls,"Zonas",header=zh); people=pd.read_excel(xls,"Responsables",header=ph)
    d.columns=[str(c).strip() for c in d.columns]; z.columns=[str(c).strip() for c in z.columns]; people.columns=[str(c).strip() for c in people.columns]
    d=d[d["ID"].notna()].copy(); d["Created date"]=pd.to_datetime(d["Created date"],errors="coerce",dayfirst=True)
    z=z.dropna(subset=["Sucursal","Zona"]).copy(); z["_key"]=z["Sucursal"].map(norm); z["Zona"]=z["Zona"].astype(str).str.replace("Zona ","",regex=False).str.strip().str.title()
    z=z[z["Zona"].isin(["Norte","Centro","Sur"])]
    aliases={"cws stracon copiapo":"copiapo","cws pozo almonte iquique":"iquique","cws atacama minerales copiapo":"copiapo"}
    loc=d["Dealer_Location"].map(norm).replace(aliases); zone_map=z.drop_duplicates("_key").set_index("_key")["Zona"].to_dict()
    d["Zona"]=loc.map(zone_map).fillna("Sin asignar")
    people=people.dropna(subset=["Zona","Responsable"]).copy(); people["Zona"]=people["Zona"].astype(str).str.replace("Zona ","",regex=False).str.strip().str.title(); people["Responsable"]=people["Responsable"].astype(str).str.strip()
    people=people[people["Zona"].isin(["Norte","Centro","Sur"])].drop_duplicates("Zona")
    resp_map=people.set_index("Zona")["Responsable"].to_dict(); d["Responsable zona"]=d["Zona"].map(resp_map).fillna("Sin responsable de zona")
    assigned=d["Assigned to id"].notna() & d["Assigned to id"].astype(str).str.strip().ne("")
    d["Días"]=((pd.Timestamp(date.today())-d["Created date"].dt.normalize()).dt.days).clip(lower=0)
    workshop=d["DR Status"].isin(["New","Open"]) & ~assigned; waiting=d["DR Status"].eq("Waiting")
    d["Gestión pendiente"]="Fuera de semáforo"; d.loc[workshop,"Gestión pendiente"]="Asignar responsable"; d.loc[waiting,"Gestión pendiente"]="Responder al concesionario"
    d["Semáforo"]="No aplica"; d.loc[workshop & d["Días"].le(4),"Semáforo"]="🟢 En plazo"; d.loc[workshop & d["Días"].between(5,6),"Semáforo"]="🟡 Por vencer"; d.loc[workshop & d["Días"].ge(7),"Semáforo"]="🔴 Antiguo"; d.loc[waiting,"Semáforo"]="⚪ Pendiente validar"
    return d,people

st.sidebar.markdown("### 📊 SEGUIMIENTO DAT v2.2")
page=st.sidebar.radio("",["Resumen","Casos","Zonas","Responsables","Configuración"])
u=st.sidebar.file_uploader("Cargar Excel semanal",type=["xlsx"])
if not u: st.info("Cargue Base.xlsx en la barra lateral para comenzar."); st.stop()
try: df,people=load_book(u.getvalue())
except Exception as e: st.error(f"No se pudo procesar el archivo: {e}"); st.stop()

st.markdown('<div class="hero">Seguimiento de informes técnicos</div>',unsafe_allow_html=True)
st.markdown('<div class="sub">Dashboard operativo · Norte, Centro y Sur · Responsables integrados</div>',unsafe_allow_html=True)
zsel=st.multiselect("Zona",["Norte","Centro","Sur","Sin asignar"],default=["Norte","Centro","Sur"])
r_opts=sorted(df["Responsable zona"].unique()); rsel=st.multiselect("Responsable de zona",r_opts,default=r_opts)
s_opts=sorted(df["DR Status"].dropna().astype(str).unique()); ssel=st.multiselect("Estado",s_opts,default=s_opts)
f=df[df["Zona"].isin(zsel)&df["Responsable zona"].isin(rsel)&df["DR Status"].isin(ssel)].copy()

if page=="Resumen":
    st.subheader("Responsables por zona")
    cols=st.columns(3)
    for c,zona in zip(cols,["Norte","Centro","Sur"]):
        row=people[people["Zona"].eq(zona)]; name=row["Responsable"].iloc[0] if len(row) else "Sin definir"
        n=len(f[f["Zona"].eq(zona)]); old=len(f[(f["Zona"].eq(zona))&(f["Semáforo"].eq("🔴 Antiguo"))])
        c.markdown(f'<div class="card"><div class="muted">{zona}</div><div class="person">👤 {name}</div><br><b>{n}</b> casos · <span style="color:#d9272e"><b>{old}</b> antiguos</span></div>',unsafe_allow_html=True)
    eligible=f[f["Gestión pendiente"].eq("Asignar responsable")]
    cards=st.columns(4); vals=[("Pendientes evaluados",len(eligible),"#244466"),("En plazo · 0–4 días",(eligible["Semáforo"]=="🟢 En plazo").sum(),"#219653"),("Por vencer · 5–6 días",(eligible["Semáforo"]=="🟡 Por vencer").sum(),"#f2a900"),("Antiguos · ≥7 días",(eligible["Semáforo"]=="🔴 Antiguo").sum(),"#d9272e")]
    for c,(lab,val,color) in zip(cards,vals): c.markdown(f'<div class="card"><div class="muted">{lab}</div><div class="k" style="color:{color}">{val}</div></div>',unsafe_allow_html=True)
    st.subheader("Semáforo por zona y responsable")
    tab=pd.crosstab([eligible["Zona"],eligible["Responsable zona"]],eligible["Semáforo"]).reindex(columns=["🟢 En plazo","🟡 Por vencer","🔴 Antiguo"],fill_value=0); tab["Total"]=tab.sum(axis=1); st.dataframe(tab,use_container_width=True)
    st.subheader("Casos que requieren atención")
    att=f[f["Semáforo"].isin(["🔴 Antiguo","🟡 Por vencer","⚪ Pendiente validar"])].sort_values("Días",ascending=False)
    show=["ID","Zona","Responsable zona","DR Status","Dealer_Location","Gestión pendiente","Días","Semáforo"]; st.dataframe(att[show],use_container_width=True,hide_index=True)
    st.download_button("Exportar seguimiento",att[show].to_csv(index=False).encode("utf-8-sig"),"seguimiento.csv","text/csv")
elif page=="Casos":
    q=st.text_input("Buscar ID, sucursal o responsable"); x=f.copy()
    if q: x=x[x.astype(str).apply(lambda c:c.str.contains(q,case=False,na=False)).any(axis=1)]
    show=["ID","Zona","Responsable zona","DR Status","Dealer_Location","Assigned to id","Created date","Días","Semáforo"]; st.dataframe(x[show],use_container_width=True,hide_index=True)
elif page=="Zonas":
    q=f.groupby(["Zona","DR Status"]).size().reset_index(name="Casos"); fig=px.bar(q,x="Zona",y="Casos",color="DR Status",barmode="stack",category_orders={"Zona":["Norte","Centro","Sur"]}); st.plotly_chart(fig,use_container_width=True)
elif page=="Responsables":
    st.subheader("Carga y antigüedad por responsable")
    summary=f.groupby(["Responsable zona","Zona"]).agg(Casos=("ID","count"),Antiguos=("Semáforo",lambda s:(s=="🔴 Antiguo").sum()),Por_vencer=("Semáforo",lambda s:(s=="🟡 Por vencer").sum()),Waiting=("DR Status",lambda s:(s=="Waiting").sum())).reset_index()
    st.dataframe(summary,use_container_width=True,hide_index=True)
    fig=px.bar(summary,x="Responsable zona",y=["Antiguos","Por_vencer"],barmode="group",labels={"value":"Casos","variable":"Indicador"}); st.plotly_chart(fig,use_container_width=True)
else:
    st.subheader("Calidad de datos")
    st.dataframe(people,use_container_width=True,hide_index=True)
    st.warning(f'{(df["DR Status"]=="Waiting").sum()} Waiting siguen pendientes de validar: falta fecha inequívoca de respuesta de fábrica.')
    unm=df[df["Zona"].eq("Sin asignar")]["Dealer_Location"].value_counts().rename_axis("Sucursal").reset_index(name="Casos"); st.dataframe(unm,use_container_width=True,hide_index=True)
