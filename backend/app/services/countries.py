"""Country names for reading a country-of-origin declaration out of label text."""

import re

# ISO 3166-1 short names, then common label spellings mapped to them.
COUNTRIES = (
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin",
    "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
    "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia",
    "Comoros", "Congo", "Costa Rica", "Côte d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czechia", "Democratic Republic of the Congo",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea",
    "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece",
    "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hong Kong", "Hungary", "Iceland", "India",
    "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania",
    "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
    "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia",
    "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines",
    "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
    "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa",
    "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan",
    "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey",
    "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
    "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
)
ALIASES = {
    "bharat": "India", "भारत": "India", "usa": "United States", "u.s.a": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "u.k": "United Kingdom", "great britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "u.a.e": "United Arab Emirates", "korea": "South Korea", "republic of korea": "South Korea",
    "prc": "China", "people's republic of china": "China", "holland": "Netherlands", "the netherlands": "Netherlands",
    "czech republic": "Czechia", "ivory coast": "Côte d'Ivoire", "burma": "Myanmar", "viet nam": "Vietnam",
    "türkiye": "Turkey", "turkiye": "Turkey", "swaziland": "Eswatini", "cape verde": "Cabo Verde", "east timor": "Timor-Leste",
    "russian federation": "Russia", "lao pdr": "Laos",
}
_NAMES = {name.casefold(): name for name in COUNTRIES} | ALIASES
# Longest first, so "South Korea" wins over "Korea" and "Guinea-Bissau" over "Guinea".
_PATTERN = re.compile(r"(?<![\w.])(" + "|".join(re.escape(n) for n in sorted(_NAMES, key=len, reverse=True)) + r")(?![\w])", re.I)


def countries_in(text: str) -> list[str]:
    """Distinct countries named in the text, in order of appearance."""
    found: list[str] = []
    for match in _PATTERN.finditer(text):
        country = _NAMES[match.group(1).casefold()]
        if country not in found:
            found.append(country)
    return found


def country_of(text: str) -> str | None:
    """The single country a declaration names; None when it names none or several."""
    found = countries_in(text)
    return found[0] if len(found) == 1 else None
