import os
import sys
import time
import torch
import numpy as np
from src.config import Config

try:
    import wandb
    _WANDB_AVAILABLE = True
except ModuleNotFoundError:
    wandb = None
    _WANDB_AVAILABLE = False

CLASS_PROMPTS = {
    "Cracks": "close-up of a single hairline crack on asphalt road surface, high resolution, realistic",
    "Patch": "rectangular asphalt patch repair on road surface, visible seams, realistic",
    "Potholes": "deep pothole on pavement road, broken asphalt edges, realistic",
    "Surface Defects": "rough road surface with raveling and weathering, deteriorated asphalt texture, realistic",
}

NEGATIVE_PROMPT = "blurry, low quality, cartoon, illustration, painting, fake, unnatural, distorted"


def generate_synthetic():
    try:
        from diffusers import StableDiffusionPipeline
    except ImportError:
        print("diffusers not installed. Run: pip install diffusers transformers accelerate")
        sys.exit(1)

    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    ).to("cuda" if torch.cuda.is_available() else "cpu")

    num_images_per_class = 100

    for class_name, prompt in CLASS_PROMPTS.items():
        class_dir = os.path.join(Config.SYNTHETIC_DIR, class_name)
        os.makedirs(class_dir, exist_ok=True)

        existing = [f for f in os.listdir(class_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        needed = max(0, num_images_per_class - len(existing))

        if needed == 0:
            print(f"{class_name}: already has {len(existing)} images, skipping")
            continue

        print(f"Generating {needed} images for {class_name}...")
        for i in range(needed):
            seed = np.random.randint(0, 2 ** 31)
            generator = torch.Generator(device=pipe.device).manual_seed(seed)

            image = pipe(
                prompt=prompt,
                negative_prompt=NEGATIVE_PROMPT,
                num_inference_steps=30,
                guidance_scale=7.5,
                generator=generator,
                height=512,
                width=512,
            ).images[0]

            image = image.resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE))
            img_path = os.path.join(class_dir, f"synth_{i:04d}.png")
            image.save(img_path)

            if (i + 1) % 20 == 0:
                print(f"  {class_name}: {i + 1}/{needed}")

    print(f"\nSynthetic dataset generated in {Config.SYNTHETIC_DIR}")
    class_counts = {}
    for class_name in Config.CLASSES:
        class_dir = os.path.join(Config.SYNTHETIC_DIR, class_name)
        count = len([f for f in os.listdir(class_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]) if os.path.isdir(class_dir) else 0
        class_counts[class_name] = count
        print(f"  {class_name}: {count} images")

    # Log to wandb
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        try:
            wandb.init(
                project=Config.WANDB_PROJECT_SYNTH,
                entity=Config.WANDB_ENTITY,
                name=f"synth-{time.strftime('%Y%m%d-%H%M%S')}",
                config={"per_class_target": num_images_per_class},
            )
            wandb.log({"per_class_count": wandb.Table(
                columns=["class", "count"],
                data=[[c, class_counts[c]] for c in Config.CLASSES],
            )})
            # Log a sample grid
            sample_images = []
            for class_name in Config.CLASSES:
                class_dir = os.path.join(Config.SYNTHETIC_DIR, class_name)
                if os.path.isdir(class_dir):
                    imgs = sorted([f for f in os.listdir(class_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
                    if imgs:
                        from PIL import Image
                        sample_images.append(Image.open(os.path.join(class_dir, imgs[0])).convert("RGB"))
            if len(sample_images) == len(Config.CLASSES):
                import matplotlib.pyplot as plt
                fig, axes = plt.subplots(1, 4, figsize=(16, 4))
                for i, (cls, img) in enumerate(zip(Config.CLASSES, sample_images)):
                    axes[i].imshow(img)
                    axes[i].set_title(cls)
                    axes[i].axis("off")
                wandb.log({"sample_grid": wandb.Image(fig)})
                plt.close(fig)
            wandb.finish()
        except Exception:
            pass


if __name__ == "__main__":
    generate_synthetic()
