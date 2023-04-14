import sys
from six import string_types, integer_types
from .exceptions import PapermillException


class PapermillTranslators(object):
    '''
    The holder which houses any translator registered with the system.
    This object is used in a singleton manner to save and load particular
    named Translator objects for reference externally.
    '''

    def __init__(self):
        self._translators = {}

    def register(self, language, translator):
        self._translators[language] = translator

    def find_translator(self, kernel_name, language):
        if kernel_name in self._translators:
            return self._translators[kernel_name]
        elif language in self._translators:
            return self._translators[language]
        raise PapermillException(
            f"No parameter translator functions specified for kernel '{kernel_name}' or language '{language}'"
        )


class Translator(object):
    @classmethod
    def translate_raw_str(cls, val):
        """Reusable by most interpreters"""
        return f'{val}'

    @classmethod
    def translate_escaped_str(cls, str_val):
        """Reusable by most interpreters"""
        if isinstance(str_val, string_types):
            str_val = str_val.encode('unicode_escape')
            if sys.version_info >= (3, 0):
                str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', r'\"')
        return f'"{str_val}"'

    @classmethod
    def translate_str(cls, val):
        """Default behavior for translation"""
        return cls.translate_escaped_str(val)

    @classmethod
    def translate_none(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_int(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_float(cls, val):
        """Default behavior for translation"""
        return cls.translate_raw_str(val)

    @classmethod
    def translate_bool(cls, val):
        """Default behavior for translation"""
        return 'true' if val else 'false'

    @classmethod
    def translate_dict(cls, val):
        raise NotImplementedError(f'dict type translation not implemented for {cls}')

    @classmethod
    def translate_list(cls, val):
        raise NotImplementedError(f'list type translation not implemented for {cls}')

    @classmethod
    def translate(cls, val):
        """Translate each of the standard json/yaml types to appropiate objects."""
        if val is None:
            return cls.translate_none(val)
        elif isinstance(val, string_types):
            return cls.translate_str(val)
        # Needs to be before integer checks
        elif isinstance(val, bool):
            return cls.translate_bool(val)
        elif isinstance(val, integer_types):
            return cls.translate_int(val)
        elif isinstance(val, float):
            return cls.translate_float(val)
        elif isinstance(val, dict):
            return cls.translate_dict(val)
        elif isinstance(val, list):
            return cls.translate_list(val)
        # Use this generic translation as a last resort
        return cls.translate_escaped_str(val)

    @classmethod
    def comment(cls, cmt_str):
        raise NotImplementedError(f'comment translation not implemented for {cls}')

    @classmethod
    def assign(cls, name, str_val):
        return f'{name} = {str_val}'

    @classmethod
    def codify(cls, parameters):
        content = f"{cls.comment('Parameters')}\n"
        for name, val in parameters.items():
            content += f'{cls.assign(name, cls.translate(val))}\n'
        return content


class PythonTranslator(Translator):
    @classmethod
    def translate_bool(cls, val):
        return cls.translate_raw_str(val)

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            [f"{cls.translate_str(k)}: {cls.translate(v)}" for k, v in val.items()]
        )
        return '{{{}}}'.format(escaped)

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'[{escaped}]'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def codify(cls, parameters):
        content = super(PythonTranslator, cls).codify(parameters)
        if sys.version_info >= (3, 6):
            # Put content through the Black Python code formatter
            import black

            fm = black.FileMode(string_normalization=False)
            content = black.format_str(content, mode=fm)
        return content


class RTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'NULL'

    @classmethod
    def translate_bool(cls, val):
        return 'TRUE' if val else 'FALSE'

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            [
                f'{cls.translate_str(k)} = {cls.translate(v)}'
                for k, v in val.items()
            ]
        )
        return f'list({escaped})'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'list({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        # Leading '_' aren't legal R variable names -- so we drop them when injecting
        while name.startswith("_"):
            name = name[1:]
        return f'{name} = {str_val}'


class ScalaTranslator(Translator):
    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        """Translate dicts to scala Maps"""
        escaped = ', '.join(
            [
                f"{cls.translate_str(k)} -> {cls.translate(v)}"
                for k, v in val.items()
            ]
        )
        return f'Map({escaped})'

    @classmethod
    def translate_list(cls, val):
        """Translate list to scala Seq"""
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'Seq({escaped})'

    @classmethod
    def comment(cls, cmt_str):
        return f'// {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'val {name} = {str_val}'


class JuliaTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'nothing'

    @classmethod
    def translate_dict(cls, val):
        escaped = ', '.join(
            [
                f"{cls.translate_str(k)} => {cls.translate(v)}"
                for k, v in val.items()
            ]
        )
        return f'Dict({escaped})'

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return f'[{escaped}]'

    @classmethod
    def comment(cls, cmt_str):
        return f'# {cmt_str}'.strip()


class MatlabTranslator(Translator):
    @classmethod
    def translate_escaped_str(cls, str_val):
        """Translate a string to an escaped Matlab string"""
        if isinstance(str_val, string_types):
            str_val = str_val.encode('unicode_escape')
            if sys.version_info >= (3, 0):
                str_val = str_val.decode('utf-8')
            str_val = str_val.replace('"', '""')
        return f'"{str_val}"'

    @staticmethod
    def __translate_char_array(str_val):
        """Translates a string to a Matlab char array"""
        if isinstance(str_val, string_types):
            str_val = str_val.encode('unicode_escape')
            if sys.version_info >= (3, 0):
                str_val = str_val.decode('utf-8')
            str_val = str_val.replace('\'', '\'\'')
        return f"\'{str_val}\'"

    @classmethod
    def translate_none(cls, val):
        return 'NaN'

    @classmethod
    def translate_dict(cls, val):
        keys = ', '.join([f"{cls.__translate_char_array(k)}" for k, v in val.items()])
        vals = ', '.join([f"{cls.translate(v)}" for k, v in val.items()])
        return 'containers.Map({{{}}}, {{{}}})'.format(keys, vals)

    @classmethod
    def translate_list(cls, val):
        escaped = ', '.join([cls.translate(v) for v in val])
        return '{{{}}}'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return f'% {cmt_str}'.strip()

    @classmethod
    def codify(cls, parameters):
        content = f"{cls.comment('Parameters')}\n"
        for name, val in parameters.items():
            content += f'{cls.assign(name, cls.translate(val))};\n'
        return content


class CSharpTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        # Can't figure out how to do this as nullable
        raise NotImplementedError("Option type not implemented for C#.")

    @classmethod
    def translate_bool(cls, val):
        return 'true' if val else 'false'

    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        """Translate dicts to nontyped dictionary"""

        kvps = ', '.join(
            ["{{ {} , {} }}".format(cls.translate_str(k), cls.translate(v)) for k, v in val.items()]
        )
        return 'new Dictionary<string,Object>{{ {} }}'.format(kvps)

    @classmethod
    def translate_list(cls, val):
        """Translate list to array"""
        escaped = ', '.join([cls.translate(v) for v in val])
        return 'new [] {{ {} }}'.format(escaped)

    @classmethod
    def comment(cls, cmt_str):
        return f'// {cmt_str}'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'var {name} = {str_val};'


class FSharpTranslator(Translator):
    @classmethod
    def translate_none(cls, val):
        return 'None'

    @classmethod
    def translate_bool(cls, val):
        return 'true' if val else 'false'

    @classmethod
    def translate_int(cls, val):
        strval = cls.translate_raw_str(val)
        return f"{strval}L" if (val > 2147483647 or val < -2147483648) else strval

    @classmethod
    def translate_dict(cls, val):
        tuples = '; '.join(
            [
                f"({cls.translate_str(k)}, {cls.translate(v)} :> IComparable)"
                for k, v in val.items()
            ]
        )
        return f'[ {tuples} ] |> Map.ofList'

    @classmethod
    def translate_list(cls, val):
        escaped = '; '.join([cls.translate(v) for v in val])
        return f'[ {escaped} ]'

    @classmethod
    def comment(cls, cmt_str):
        return f'(* {cmt_str} *)'.strip()

    @classmethod
    def assign(cls, name, str_val):
        return f'let {name} = {str_val}'


# Instantiate a PapermillIO instance and register Handlers.
papermill_translators = PapermillTranslators()
papermill_translators.register("python", PythonTranslator)
papermill_translators.register("R", RTranslator)
papermill_translators.register("scala", ScalaTranslator)
papermill_translators.register("julia", JuliaTranslator)
papermill_translators.register("matlab", MatlabTranslator)
papermill_translators.register(".net-csharp", CSharpTranslator)
papermill_translators.register(".net-fsharp", FSharpTranslator)


def translate_parameters(kernel_name, language, parameters):
    return papermill_translators.find_translator(kernel_name, language).codify(parameters)
