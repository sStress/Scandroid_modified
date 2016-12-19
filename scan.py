
# coding: utf-8

# In[ ]:

import re, os
from itertools import chain

def encode(ch): return chr(ord(ch) & 0x3F)
def decode(ch): return chr(ord(ch) | 0x40)

SIBILANTS = '40xzjgsc'
MULTISUFFIX = ('ible', 'able')
STRESSSUFFIX = ('tion', 'sion', 'tiou', 'ciou', 'tious',
                'cious', 'cion', 'gion', 'giou', 'gious')
PREFIXES = ('a', 'as', 'be', 'con', 'de', 'di', 'ex', 're', 'un', 'en')

def handleCiV(match):	  # encode [st] and i but not following vowel
    c1 = encode(match.group()[0])
    c2 = encode(match.group()[1])
    return c1 + c2 + match.group()[2]
def handleCC(match):	  # adjusted for third-char test! expand this opport.?
    ret = encode(match.group()[0]) + encode(match.group()[1])
    if len(match.group()) > 2: ret += match.group()[2]
    return ret
def handleVyV(match):
    return match.group()[0] + encode(match.group()[1]) + match.group()[2]

class Syllabizer:
    def __init__(self):
        self.suffixes = re.compile(r""" [^aeiouhr]y\b | er\b | age | est |
                ing | ness\b | less | ful | ment\b | time\b | [st]ion |
                [ia]ble\b | [ct]ial | [ctg]iou | [ctg]ious
            """, re.VERBOSE)
#	| ical\b | icle\b | ual\b | ism \b | [ae]ry\b		# don't work (as 2-syl)
      # Note: left out special-character "*ag$" and "tim$" -- don't understand!
      # final syllable spelled with liquid or nasal and silent 'e'
        self.liquidterm = re.compile(r" [^aeiouy] [rl] e \b", re.X)
        # the collection of special-character groups
        self.finalE = re.compile(r" [^aeiouy] e \b ", re.X)
        self.CiVcomb = re.compile(r" [st] i [aeiouy] ", re.X)
        self.CCpair = re.compile(r" [cgprstw] h | gn |  gu[aeiouy] | qu | ck",
                                                                         re.X)
        self.VyVcomb = re.compile(r" [aeiou] y [aeiou]", re.X) 
    # vowel pairs reliably disyllabic (not 'ui' ('juice' vs 'intuition'! some 
    # 'ue' missed ('constituent'), some 'oe' ('poem'))
        self.sylvowels = re.compile(r" [aeiu] o | [iu] a | iu", re.X)
    # divisions should fall before or after, not within, these consonant pairs
        self.splitLeftPairs = re.compile(r""" [bdfk%02] [rl] | g [rln] |
                                          [tw] r | p [rlsn] s [nml]""", re.X)

    def Syllabize(self, word):
        if len(word) < 3: return [word.upper()]	# 'ax' etc
        self.wd = word.lower()
        self.sylBounds = []
        self.Preliminaries()
        self.SpecialCodes()
        self.DivideCV()
        stressed = self.StressGuesser(word)
        self.sylBounds.insert(0, 0)		# ease the calc of syllable indices
        self.sylBounds.append(len(word))	# 	within the word
        listOfSyls = []
        listOfStressSyls = []
        i = 0
        for s in self.sylBounds:
            if not s: continue
            i += 1
            if i != stressed:
                listOfSyls.append(word[self.sylBounds[i-1]:s])
            else:
                listOfSyls.append(word[self.sylBounds[i-1]:s].upper())
        return listOfSyls
    
    def SyllList(self, word):
        if len(word) < 3: return [1]	# 'ax' etc
        self.wd = word.lower()
        self.sylBounds = []
        self.Preliminaries()
        self.SpecialCodes()
        self.DivideCV()
        stressed = self.StressGuesser(word)
        self.sylBounds.insert(0, 0)		# ease the calc of syllable indices
        self.sylBounds.append(len(word))	# 	within the word
        listOfStressSyls = []
        i = 0
        for s in self.sylBounds:
            if not s: continue
            i += 1
            if i != stressed:
                listOfStressSyls.append(0)
            else:
                listOfStressSyls.append(1)
        return listOfStressSyls
          

    def Preliminaries(self):
        apostrophe = self.wd.find("\'", -2)	# just at end of word ('twas)
        if apostrophe != -1:		# poss.; check if syllabic and remove 
            if (self.wd[-1] != '\'' and self.wd[-1] in 'se'
                                    and self.wd[-2] in SIBILANTS):
                self.sylBounds.append(apostrophe)
            self.wd = self.wd[:apostrophe]	# cut off ' or 's until last stage
        # cut final s/d from plurals/pasts if not syllabic
        self.isPast = self.isPlural = False	 # defaults used also for suffixes
        if re.search(r"[^s]s\b", self.wd):
            self.isPlural = True	# terminal single s (DUMB!)
        if re.search(r"ed\b", self.wd):
            self.isPast = True		# terminal 'ed'
        if self.isPast or self.isPlural:
            self.wd = self.wd[:-1]
        # final-syl test turns out to do better work *after* suffices cut off
        self.FindSuffix()
        # if final syllable is l/r+e, reverse letters for processing as syll.
        if len(self.wd) > 3 and self.liquidterm.search(self.wd):
            self.wd = self.wd[:-2] + self.wd[-1] + self.wd[-2]

    def FindSuffix(self):
        """Identify any known suffixes, mark off
        as syllables and possible stresses.
        
        Syllables are stored in a class-wide compiled RE. We identify them and
        list them backwards so as to "cut off" the last first. We consult a
        global-to-module list of those that force stress on previous syllable.
        """
        self.numSuffixes = 0
        self.forceStress = 0
        resultslist = []
        for f in self.suffixes.finditer(self.wd):
            resultslist.append((f.group(), f.start()))
        if not resultslist: return
        # make sure *end* of word is in list! otherwise, 'DESP erate'
        if resultslist[-1][1] + len(resultslist[-1][0]) < len(self.wd):
            return
        resultslist.reverse()
        for res in resultslist:
            # if no vowel left before, false suffix ('singing')
            # n.b.: will choke on 'quest' etc! put in dictionary, I guess
            if not re.search('[aeiouy]', self.wd[:res[1]]): break
            if res[0] == 'ing' and self.wd[res[1]-1] == self.wd[res[1]-2]:
                self.sylBounds.append(res[1] - 1)	# freq special case
            else: self.sylBounds.append(res[1])	# sorted later
            self.wd = self.wd[:res[1]]
            self.numSuffixes += 1
            if res[0] in STRESSSUFFIX:
                self.forceStress = 0 - len(self.sylBounds)
            if res[0] in MULTISUFFIX:
                # tricky bit! it *happens* that secondary division in all these
                # comes after its first character; NOT inevitable!
                # also does not allow for 3-syl: 'ically' (which are reliable!)
                self.sylBounds.append(res[1]+1)
                self.numSuffixes += 1

    def SpecialCodes(self):
        """Encode character-combinations so as to trick DivideCV.
        
        The combinations are contained in regexes compiled in the class's 
        __init__. Encoding (*not* to be confused with Unicode functions!) is
        done by small functions outside of (and preceding) the class.
        
        The combinations in Paul Holzer's original code have been supplemented
        and tweaked in various ways. For example, the original test for [iy]V
        is poor; 'avionics' defeats it; so we leave that to a new
        disyllabic-vowel test.
        
        The messy encoding-and-sometimes-decoding of nonsyllabic final 'e' 
        after a C seems the best that can be done, though I hope not. 
        """
        if re.search(r"[^aeiouy]e\b", self.wd): # nonsyllabic final e after C
            if ((not self.isPlural or self.wd[-2] not in SIBILANTS) and
                                 (not self.isPast or self.wd[-2] not in 'dt')):
                self.wd = self.wd[:-1] + encode(self.wd[-1])
            if not re.search(r"[aeiouy]", self.wd):		# any vowel left??
                self.wd = self.wd[:-1] + 'e'		# undo the encoding
        self.wd = self.CiVcomb.sub(handleCiV, self.wd)
        self.wd = self.CCpair.sub(handleCC, self.wd)
        self.wd = self.VyVcomb.sub(handleVyV, self.wd)

    def DivideCV(self):
        """Divide the word among C and V groups to fill the sylBounds list.
        
        Here, and here alone, we need to catch e-with-grave-accent to count it
        as not only a vowel but syllabic ('an aged man' vs. 'aged beef'). Other
        special characters might be useful to recognize, but won't make the 
        same syllabic difference.
        """
        unicodeVowels = u"[ae\N{LATIN SMALL LETTER E WITH GRAVE}iouy]+"
        uniConsonants = u"[^ae\N{LATIN SMALL LETTER E WITH GRAVE}iouy]+"
        firstvowel = re.search(unicodeVowels, self.wd).start()
        for v in re.finditer(unicodeVowels, self.wd):
            lastvowel = v.end()		# replaced for each group, last sticks
            disyllabicvowels = self.sylvowels.search(v.group())
            if disyllabicvowels:
                self.sylBounds.append(v.start() + disyllabicvowels.start() + 1)
        for cc in re.finditer(uniConsonants, self.wd):
            if cc.start() < firstvowel or cc.end() >= lastvowel: continue
            numcons = len(cc.group())
            if numcons < 3: pos = cc.end() - 1	# before single C or betw. 2
            elif numcons > 3: pos = cc.end() - 2	# before penult C
            else:		# 3 consonants, divide 1/2 or 2/1?
                cg = cc.group()		# our CCC cluster
                if cg[-3] == cg[-2] or self.splitLeftPairs.search(cg):
                    pos = cc.end() - 2			# divide 1/2
                else: pos = cc.end() - 1		# divide 2/1
            if not self.wd[pos-1].isalpha() and not self.wd[pos].isalpha():
                self.sylBounds.append(pos-1)
            else: self.sylBounds.append(pos)

    def StressGuesser(self, origword):
        """Try to locate stressed syllable; return *1*-based index.
        
        Use Nessly's Default (not great), with hints from stress-forcing
        suffixes, a few prefixes, and number of suffixes. Nessly's Default
        for disyllables is more useful if we apply it also before suffixes.
        
        As I've added suffix and prefix twists to Nessly, I've steadily
        *compromised* Nessly. (Example: 'for EV er' in older version, now
        'FOR ev er'; it happens that the 3+-syl version of Nessly works for
        this word while the 2-syl version applied after -er is removed doesn't.
        This in-between state should probably be resolved, but resolving it
        well is not easy. Adding 'en' to prefixes fixes 'encourage' but breaks
        'entry'. At some point the returns from new compromises and special
        cases diminish; there will *always* be an exceptions dictionary.
        """
        numsyls = len(self.sylBounds) + 1
        if numsyls == 1: return 1
        self.sylBounds.sort()		# suffixes may have been marked first
        if self.forceStress:		# suffixes like 'tion', 'cious'
            return numsyls + self.forceStress
        if numsyls - self.numSuffixes == 1:	# pretty reliable I think
            return 1
        isprefix = self.wd[:self.sylBounds[0]] in PREFIXES
        if numsyls - self.numSuffixes == 2:	# Nessly w/ suffix twist
            if isprefix: return 2
            else: return 1
        elif isprefix and (numsyls - self.numSuffixes == 3):
            return 2
        else:	# Nessley: 3+ syls, str penult if closed, else antepenult
            # syl n is origword[self.sylBounds[n-1]:self.sylBounds[n]-1];  so?
            if (origword[self.sylBounds[-1] - 1]
                                  not in 'aeiouy'): # last char penult
                retstress = numsyls - 1				# if closed, stress penult
            else: retstress = numsyls - 2			# else, antepenult
            if self.numSuffixes == numsyls:
                retstress -= 1
        return retstress
    
    
def Accent():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files:
        s = Syllabizer()
        file_input = open(f, 'r', encoding = 'utf-8')
        data_dir = f.split('.')[0] + '_data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        text = file_input.read()
        file_stressed = open(os.path.join(dname,data_dir,'text_stressed.txt'), 'w')
        binary_vectors = open(os.path.join(dname,data_dir,'binary_vectors.txt'), 'w')
        stress_indices = open(os.path.join(dname,data_dir,'indices_stressed_syl.txt'), 'w')

        lines = text.split('\n')
        

        for l in lines:
            words = [w.strip('"') for w in l.split()]
            line_stressed = list()
            list_stressed_syls = list()

            if words != list():
                for w in words:
                    if not w.isdigit():
                        res = s.Syllabize(w)
                        res_bin = s.SyllList(w)
                        line_stressed.append(res)
                        list_stressed_syls.append(res_bin)


                file_stressed.write(str(list(chain.from_iterable(line_stressed))))
                file_stressed.write('\n')

                chained = list(chain.from_iterable(list_stressed_syls))
                binary_vectors.write(str(chained))
                binary_vectors.write('\n')

                str_ind_list = [i for i, x in enumerate(chained) if x == 1]
                stress_indices.write(str(str_ind_list))
                stress_indices.write('\n')

        file_input.close()
        file_stressed.close()
        binary_vectors.close()
        stress_indices.close()
        
#try: 
Accent()
#except AttributeError:
    #pass

