"""
descriptor_produccion.py

Descriptor global de producción: VLAD + DINOv3-vitl16 (SAT-493M), la
configuración ganadora de las 6 comparadas en
13_comparar_retrieval_metodos.py sobre las 76 queries validadas:

    rank mediana=1  media=1.2  top-1=89.5%  top-5=98.7%  top-10=100.0%

Backbone DINOv3 (torch.hub, pesos locales) + agregación VLAD, con el
vocabulario ajustado por k-means sobre los propios parches de la
gallery (zero-shot, sin entrenar ninguna red).

Requisitos:
    pip install torch torchvision pillow numpy scikit-learn
    git clone --depth 1 https://github.com/facebookresearch/dinov3 dinov3_repo
    Pesos .pth en dinov3_weights/ (ver README del proyecto), ambas como
    carpetas hermanas de este repositorio.
"""
import os

import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from sklearn.cluster import KMeans

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

REPO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dinov3_repo")
WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dinov3_weights")
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "dinov3_vitl16_pretrain_sat493m-eadcf0ff.pth")

BACKBONE_TAG = "dinov3_vitl16_sat"
PATCH_SIZE = 16    # DINOv3 usa parches de 16x16
TARGET_SIZE = 512  # lado mayor de la imagen tras el resize, múltiplo de 16

N_CLUSTERS = 32          # tamaño del vocabulario VLAD (K)
N_PATCHES_FIT = 200_000  # nº máximo de parches muestreados para ajustar k-means

_model = None
_codebook = None


def load_model():
    global _model
    if _model is None:
        print(f"Cargando DINOv3 (vitl16_sat) desde pesos locales {WEIGHTS_PATH}...")
        _model = torch.hub.load(
            REPO_DIR, "dinov3_vitl16", source="local",
            weights=WEIGHTS_PATH, pretrained=True,
        )
        _model.eval().to(DEVICE)
    return _model


def _round_to_patch(value, patch_size=PATCH_SIZE):
    return max(patch_size, int(round(value / patch_size)) * patch_size)


def preprocess(img_path):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    scale = TARGET_SIZE / max(w, h)
    new_w = _round_to_patch(w * scale)
    new_h = _round_to_patch(h * scale)

    transform = T.Compose([
        T.Resize((new_h, new_w)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return transform(img).unsqueeze(0)


@torch.no_grad()
def get_patch_tokens(img_path):
    """Tokens de parche crudos (N, C) de DINOv3, para que VLAD los agregue."""
    model = load_model()
    x = preprocess(img_path).to(DEVICE)
    features = model.forward_features(x)
    return features["x_norm_patchtokens"].squeeze(0).cpu().numpy()


def fit_codebook(gallery_rows, gallery_dir, force_refit=False):
    """Ajusta (o carga de caché) el vocabulario VLAD con k-means sobre
    parches muestreados de la gallery."""
    global _codebook
    if _codebook is not None and not force_refit:
        return _codebook

    codebook_path = f"vlad_codebook_{BACKBONE_TAG}.npy"
    if not force_refit and os.path.exists(codebook_path):
        print(f"Usando vocabulario VLAD cacheado de '{codebook_path}'")
        _codebook = np.load(codebook_path)
        return _codebook

    print(f"Ajustando vocabulario VLAD (K={N_CLUSTERS}) sobre parches de la "
          f"gallery (esto solo tarda la primera vez)...")
    all_patches = []
    for i, row in enumerate(gallery_rows):
        path = f"{gallery_dir}/{row['file']}"
        all_patches.append(get_patch_tokens(path))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(gallery_rows)} tiles procesados (extracción de parches)")
    all_patches = np.concatenate(all_patches, axis=0)  # (N_total, C)
    print(f"  {len(all_patches)} parches en total")

    if len(all_patches) > N_PATCHES_FIT:
        rng = np.random.default_rng(0)
        idx = rng.choice(len(all_patches), N_PATCHES_FIT, replace=False)
        all_patches = all_patches[idx]

    print(f"  Ajustando k-means (K={N_CLUSTERS}) sobre {len(all_patches)} parches muestreados...")
    km = KMeans(n_clusters=N_CLUSTERS, n_init=4, random_state=0)
    km.fit(all_patches)
    codebook = km.cluster_centers_.astype(np.float32)  # (K, C)
    np.save(codebook_path, codebook)
    print(f"Vocabulario VLAD guardado en '{codebook_path}'")
    _codebook = codebook
    return codebook


def vlad_aggregate(patch_tokens, codebook):
    """patch_tokens: (N, C), codebook: (K, C) -> descriptor VLAD (K*C,)
    normalizado (power-norm + L2, estándar en VLAD/NetVLAD)."""
    # ||a-b||^2 = ||a||^2 + ||b||^2 - 2*a.b, más barato que expandir (N,K,C)
    a2 = np.sum(patch_tokens ** 2, axis=1, keepdims=True)      # (N,1)
    b2 = np.sum(codebook ** 2, axis=1, keepdims=True).T        # (1,K)
    dists = a2 + b2 - 2 * patch_tokens @ codebook.T             # (N,K)
    assign = np.argmin(dists, axis=1)

    K, C = codebook.shape
    vlad = np.zeros((K, C), dtype=np.float32)
    for k in range(K):
        mask = assign == k
        if np.any(mask):
            vlad[k] = (patch_tokens[mask] - codebook[k]).sum(axis=0)

    vlad = vlad.flatten()
    vlad = np.sign(vlad) * np.sqrt(np.abs(vlad) + 1e-12)  # signed sqrt (power-norm)
    norm = np.linalg.norm(vlad)
    if norm > 0:
        vlad = vlad / norm
    return vlad.astype(np.float32)


def get_gallery_embeddings(gallery_rows, gallery_dir, force_recompute=False):
    codebook = fit_codebook(gallery_rows, gallery_dir, force_refit=force_recompute)
    cache_path = f"gallery_embeddings_vlad_{BACKBONE_TAG}.npz"
    fingerprint = "|".join(row["file"] for row in gallery_rows) + f"|K={len(codebook)}"

    if not force_recompute and os.path.exists(cache_path):
        cached = np.load(cache_path, allow_pickle=True)
        if str(cached["fingerprint"]) == fingerprint:
            print(f"Usando embeddings VLAD cacheados de '{cache_path}' ({len(gallery_rows)} tiles)")
            return cached["embeddings"]
        print("La gallery/vocabulario VLAD cambió respecto al caché -> recalculando.")

    print(f"Embebiendo {len(gallery_rows)} parches de la gallery con VLAD+DINOv3-SAT...")
    descs = []
    for i, row in enumerate(gallery_rows):
        path = f"{gallery_dir}/{row['file']}"
        descs.append(vlad_aggregate(get_patch_tokens(path), codebook))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(gallery_rows)} parches procesados")

    embeddings = np.stack(descs)
    np.savez(cache_path, embeddings=embeddings, fingerprint=fingerprint)
    print(f"Embeddings guardados en '{cache_path}'")
    return embeddings


def get_descriptor(img_path):
    if _codebook is None:
        raise RuntimeError(
            "Vocabulario VLAD no ajustado -- llama a get_gallery_embeddings(gallery_rows, gallery_dir) "
            "antes de pedir descriptores de queries."
        )
    return vlad_aggregate(get_patch_tokens(img_path), _codebook)
