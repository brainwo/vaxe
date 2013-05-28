import vim, re, HTMLParser
import xml.etree.ElementTree as ET
import json



# This is the python portion of the completion script.  Call it with the *name*
# of the input vimscript variable, "complete_output_var".  This should contain
# the output from the --display compiler directive.  base_var is an optional
# partial word to use for filtering completions.
# The output is given in "output_var", which is likewise the name of the
# vimscript variable to write. This variable contains a dictionary formatted
# appropriately for an omnifunc.  "base_var" contains an optional partial word
# to filter for
def complete(complete_output_var, output_var, base_var , alter_var, collapse_var):
    complete_output = vim.eval(complete_output_var)
    base = vim.eval(base_var)
    alter_sig = vim.eval(alter_var) != '0'
    collapse_overload = vim.eval(collapse_var) != '0'
    if complete_output is None: complete_output = ''
    completes = []

    # wrap in a tag to prevent parsing errors
    root = ET.XML("<output>" + complete_output + "</output>")

    fields = root.findall("list/i")
    types = root.findall("type")
    completes = []

    if len(fields) > 0: # field completion
        def fieldxml2completion(x):
            word = x.attrib["n"]
            menu = x.find("t").text
            info = x.find("d").text
            menu = '' if menu is None else menu
            if info is None:
                info = ['']
            else:
                # get rid of leading/trailing ws/nl
                info = info.strip()
                # split and collapse extra whitespace
                info = [re.sub(r'\s+',' ',s.strip()) for s in info.split('\n')]

            abbr = word
            kind = 'v'
            if  menu == '': kind = 'm'
            elif re.search("\->", menu):
                kind = 'f' # if it has a ->
                if alter_sig:
                    menu = alter_signature(menu)
                word += "("

            return {  'word': word, 'info': info, 'kind': kind
                    ,'menu': menu, 'abbr': abbr, 'dup':1 }

        completes = map(fieldxml2completion, fields)
    elif len(types) > 0: # function type completion
        otype = types[0]
        h = HTMLParser.HTMLParser()
        word = ' '
        info = [h.unescape(otype.text).strip()]
        abbr = info[0]
        if alter_sig:
            abbr = alter_signature(abbr)
        completes= [{'word':word,'info':info, 'abbr':abbr, 'dup':1}]

    if base != '':
        completes = [c for c in completes if re.search("^" + base, c['word'])]

    if collapse_overload:
        dict_complete = dict()
        def complete_exists(c):
            if c in dict_complete:
                dict_complete[c] += 1
                return True
            else:
                dict_complete[c] = 1
                return False
        completes = [c for c in completes if not complete_exists(c['abbr'])]
        for c in completes:
            if dict_complete[c['abbr']] > 1:
                c['menu'] = "@:overload " + c['menu']

    vim.command("let " + output_var + " = " + json.dumps(completes))

# simple script to grab lists of locations from display-mode completions
def locations(complete_output_var, output_var):
    complete_output = vim.eval(complete_output_var)
    vim.command("let " + output_var + " = " + json.dumps(completes))
    # wrap in a tag to prevent parsing errors
    root = ET.XML("<output>" + complete_output + "</output>")
    pos = root.findall("pos")
    if len(pos) > 0:
        return [p.text for p in pos]
    else:
        return []

def alter_signature(sig):
    paren = 0
    last_string = ''
    final_expr = ''
    for i in xrange(len(sig)):
        c = sig[i]
        if c == "(":
            paren += 1
            final_expr += re.sub('->',",", last_string)
            last_string = c
        elif c == ")":
            last_string += c
            paren -=1
            if paren == 0:
                final_expr += last_string
                last_string = ''
        else:
            last_string += c

    final_expr = final_expr + re.sub('\s*->\s*', ",", last_string)
    parts = final_expr.split(',')
    ret_val = parts.pop()
    if ret_val == "Void":
        ret_val = ''
    else:
        ret_val = " : " + ret_val

    if len(parts) ==1 and parts[0] == "Void":
        parts[0] = ''

    final_expr = '(' + ", ".join(parts) + ')' + ret_val
    return final_expr
