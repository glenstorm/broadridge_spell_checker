// Spelling corrector.
//
// A correction is a dictionary word within two edits of the input word.
// An edit inserts one character or deletes one character. Two insertions
// are legal only when the inserted characters are not adjacent in the
// longer word; two deletions are legal only when the deleted characters
// are not adjacent in the longer word. One insertion together with one
// deletion (a replacement or a move) has no adjacency restriction.
//
// One-edit corrections replace two-edit corrections whenever any exist.
// Comparisons are case-insensitive. Exact matches keep the text's case;
// corrections are printed in the dictionary's case, in dictionary order.

#include <algorithm>
#include <cstddef>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

bool isWhitespace(unsigned char c) {
    return c == ' ' || c == '\t' || c == '\v' || c == '\f' || c == '\r';
}

std::string toLowerAscii(const std::string& text) {
    std::string lower(text);
    for (char& ch : lower) {
        const unsigned char c = static_cast<unsigned char>(ch);
        if (c >= 'A' && c <= 'Z') {
            ch = static_cast<char>(c - 'A' + 'a');
        }
    }
    return lower;
}

// `text` with the character at `index` removed.
std::string deleteOne(const std::string& text, std::size_t index) {
    std::string result;
    result.reserve(text.size() - 1);
    result.append(text, 0, index);
    result.append(text, index + 1, std::string::npos);
    return result;
}

// `text` with the characters at `first` and `second` removed.
// `first` < `second` and the two positions are not adjacent.
std::string deleteTwo(const std::string& text, std::size_t first, std::size_t second) {
    std::string result;
    result.reserve(text.size() - 2);
    result.append(text, 0, first);
    result.append(text, first + 1, second - first - 1);
    result.append(text, second + 1, std::string::npos);
    return result;
}

class SpellChecker {
public:
    void add(const std::string& word) {
        std::string lower = toLowerAscii(word);
        if (exact_.find(lower) != exact_.end()) {
            return;
        }

        const std::size_t index = dictionary_.size();
        dictionary_.push_back(Entry{word, lower});
        exact_.emplace(std::move(lower), index);
        indexDeletions(index);
    }

    std::string correct(const std::string& word) const {
        const std::string lower = toLowerAscii(word);
        if (exact_.find(lower) != exact_.end()) {
            return word;
        }

        std::vector<std::size_t> matches = matchDistance(lower, 1);
        if (matches.empty()) {
            matches = matchDistance(lower, 2);
        }
        return format(word, matches);
    }

private:
    struct Entry {
        std::string text;
        std::string lower;
    };

    using IndexList = std::vector<std::size_t>;
    using IndexMap = std::unordered_map<std::string, IndexList>;

    void addIndex(IndexMap& indexes, const std::string& key, std::size_t index) {
        IndexList& bucket = indexes[key];
        if (bucket.empty() || bucket.back() != index) {
            bucket.push_back(index);
        }
    }

    void indexDeletions(std::size_t index) {
        const std::string& text = dictionary_[index].lower;
        const std::size_t length = text.size();

        for (std::size_t i = 0; i < length; ++i) {
            addIndex(oneDeletion_, deleteOne(text, i), index);
        }
        for (std::size_t i = 0; i + 2 < length; ++i) {
            for (std::size_t j = i + 2; j < length; ++j) {
                addIndex(twoDeletions_, deleteTwo(text, i, j), index);
            }
        }
    }

    static void uniqueSorted(IndexList& indexes) {
        std::sort(indexes.begin(), indexes.end());
        indexes.erase(std::unique(indexes.begin(), indexes.end()), indexes.end());
    }

    // Dictionary words reachable by `distance` edits (1 or 2), in dictionary order.
    IndexList matchDistance(const std::string& lower, int distance) const {
        IndexList matches;
        const std::size_t length = lower.size();

        if (distance == 1) {
            for (std::size_t i = 0; i < length; ++i) {
                const auto found = exact_.find(deleteOne(lower, i));
                if (found != exact_.end()) {
                    matches.push_back(found->second);
                }
            }
            const auto found = oneDeletion_.find(lower);
            if (found != oneDeletion_.end()) {
                matches.insert(matches.end(), found->second.begin(), found->second.end());
            }
        } else {
            for (std::size_t i = 0; i + 2 < length; ++i) {
                for (std::size_t j = i + 2; j < length; ++j) {
                    const auto found = exact_.find(deleteTwo(lower, i, j));
                    if (found != exact_.end()) {
                        matches.push_back(found->second);
                    }
                }
            }
            const auto inserted = twoDeletions_.find(lower);
            if (inserted != twoDeletions_.end()) {
                matches.insert(matches.end(), inserted->second.begin(), inserted->second.end());
            }
            for (std::size_t i = 0; i < length; ++i) {
                const auto found = oneDeletion_.find(deleteOne(lower, i));
                if (found == oneDeletion_.end()) {
                    continue;
                }
                for (const std::size_t index : found->second) {
                    if (dictionary_[index].lower != lower) {
                        matches.push_back(index);
                    }
                }
            }
        }

        uniqueSorted(matches);
        return matches;
    }

    std::string format(const std::string& word, const IndexList& matches) const {
        if (matches.empty()) {
            std::string result;
            result.reserve(word.size() + 3);
            result.push_back('{');
            result.append(word);
            result.append("?}");
            return result;
        }
        if (matches.size() == 1) {
            return dictionary_[matches[0]].text;
        }

        std::string result;
        result.push_back('{');
        for (std::size_t i = 0; i < matches.size(); ++i) {
            if (i != 0) {
                result.push_back(' ');
            }
            result.append(dictionary_[matches[i]].text);
        }
        result.push_back('}');
        return result;
    }

    std::vector<Entry> dictionary_;
    std::unordered_map<std::string, std::size_t> exact_;
    IndexMap oneDeletion_;
    IndexMap twoDeletions_;
};

void addWords(SpellChecker& checker, const std::string& line) {
    std::size_t i = 0;
    const std::size_t length = line.size();
    while (i < length) {
        while (i < length && isWhitespace(static_cast<unsigned char>(line[i]))) {
            ++i;
        }
        if (i >= length) {
            break;
        }
        const std::size_t start = i;
        while (i < length && !isWhitespace(static_cast<unsigned char>(line[i]))) {
            ++i;
        }
        checker.add(line.substr(start, i - start));
    }
}

std::string correctLine(const SpellChecker& checker, const std::string& line) {
    std::string result;
    result.reserve(line.size());
    std::size_t i = 0;
    const std::size_t length = line.size();
    while (i < length) {
        if (isWhitespace(static_cast<unsigned char>(line[i]))) {
            result.push_back(line[i]);
            ++i;
            continue;
        }
        const std::size_t start = i;
        while (i < length && !isWhitespace(static_cast<unsigned char>(line[i]))) {
            ++i;
        }
        result.append(checker.correct(line.substr(start, i - start)));
    }
    return result;
}

void stripCarriageReturn(std::string& line) {
    if (!line.empty() && line.back() == '\r') {
        line.pop_back();
    }
}

void stripUtf8Bom(std::string& line) {
    if (line.size() >= 3 &&
        static_cast<unsigned char>(line[0]) == 0xEF &&
        static_cast<unsigned char>(line[1]) == 0xBB &&
        static_cast<unsigned char>(line[2]) == 0xBF) {
        line.erase(0, 3);
    }
}

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    SpellChecker checker;
    std::string line;
    bool readingDictionary = true;
    bool firstLine = true;

    while (std::getline(std::cin, line)) {
        stripCarriageReturn(line);
        if (firstLine) {
            stripUtf8Bom(line);
            firstLine = false;
        }

        if (line == "===") {
            if (readingDictionary) {
                readingDictionary = false;
                continue;
            }
            break;
        }

        if (readingDictionary) {
            addWords(checker, line);
        } else {
            std::cout << correctLine(checker, line) << '\n';
        }
    }

    return 0;
}
