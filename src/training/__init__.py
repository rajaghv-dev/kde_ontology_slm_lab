"""Training recipes for the KDE small-language-model lab.

This package collects *recipe scripts* that translate ``configs/training.yaml``
into actual fine-tuning launches. Per the lab's policy ("recipes only, no
auto-downloads"), every script here supports ``--dry-run`` and keeps heavy
imports (torch / transformers / trl / peft / unsloth / bitsandbytes) inside
``main()`` so importing the module costs nothing.

Modules:

* ``lora_config``      — dataclass that resolves the active training profile.
* ``qlora_config``     — QLoRA wrapper over ``LoRAConfig`` (4-bit base weights).
* ``hf_peft_sft``      — SFT via ``trl.SFTTrainer`` + ``peft.LoraConfig``.
* ``unsloth_sft``      — SFT via Unsloth's ``FastLanguageModel``.
* ``grpo_optional``    — advanced/optional GRPO with KDE-ontology rewards.
* ``merge_adapter``    — fold a LoRA adapter into the base weights.
* ``export_gguf``      — wrap ``llama.cpp`` to produce a quantised GGUF.
* ``train_router``     — rule-based query -> adapter classifier (pure Python).
"""
