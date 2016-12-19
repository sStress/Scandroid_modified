# Scandroid_modified
Function scan.py is a modified version of Syllabilizer from Scandroid. It divides words in text files into syllables and accentize them. Yet it is not perfect, but the division in syllables works well.

txt-files in the folder are prepared files of raw text to be accentized.

Folders with _data include 3 txt-files: 

-- binary_vectors.txt with binary vectors (0 - not stressed syllable, 1 - stressed syllable).

-- indices_stressed_syl.txt with positions (indices) of stressed syllables.

-- text_stressed.txt is the accentized text (stressed syllables are writen in CAPITAL letters).
