package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"path"
	"regexp"
	"sort"
	"strings"
	"time"
)

const InputDirectory = "./out"

type Segment struct {
	Name    string    `json:"name"`
	Created time.Time `json:"created"`
	ASR     string    `json:"asr"`
	English string    `json:"en"`
	Chinese string    `json:"cn"`
}

func listFilesSortedByCreationTime(dir string) ([]*Segment, error) {
	filesInfo, err := ioutil.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	files := make([]*Segment, 0, len(filesInfo))
	for _, fileInfo := range filesInfo {
		if !strings.HasSuffix(strings.ToLower(fileInfo.Name()), ".ts") {
			continue
		}

		if !fileInfo.IsDir() {
			created, err := getCreationTime(dir, fileInfo)
			if err != nil {
				return nil, err
			}
			files = append(files, &Segment{Name: fileInfo.Name(), Created: created})
		}
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Name < files[j].Name
	})

	return files, nil
}

func getCreationTime(dir string, fileInfo os.FileInfo) (time.Time, error) {
	filePath := fmt.Sprintf("%s/%s", dir, fileInfo.Name())
	file, err := os.Open(filePath)
	if err != nil {
		return time.Time{}, err
	}
	defer file.Close()

	fileStat, err := file.Stat()
	if err != nil {
		return time.Time{}, err
	}

	return fileStat.ModTime(), nil
}

func isAlphaNumeric(s string) bool {
	re, err := regexp.Compile("^[a-zA-Z0-9_\\-]+$")
	if err != nil {
		return false
	}
	return re.MatchString(s)
}

func main() {
	http.HandleFunc("/api/segments", func(w http.ResponseWriter, r *http.Request) {
		if err := func() error {
			q := r.URL.Query()
			in := q.Get("in")
			if in == "" || !isAlphaNumeric(in) {
				return fmt.Errorf("invalid query: in %s", in)
			}

			fileInfos, err := listFilesSortedByCreationTime(path.Join(InputDirectory, in))
			if err != nil {
				return err
			}

			for _, fileInfo := range fileInfos {
				basename := path.Base(fileInfo.Name)
				filename := basename[0 : len(basename)-len(path.Ext(basename))]
				if b, err := ioutil.ReadFile(path.Join(InputDirectory, in, fmt.Sprintf("%v.asr.final.txt", filename))); err == nil {
					fileInfo.ASR = string(b)
				}
				if b, err := ioutil.ReadFile(path.Join(InputDirectory, in, fmt.Sprintf("%v.trans.en.txt", filename))); err == nil {
					fileInfo.English = string(b)
				}
				if b, err := ioutil.ReadFile(path.Join(InputDirectory, in, fmt.Sprintf("%v.trans.cn.txt", filename))); err == nil {
					fileInfo.Chinese = string(b)
				}
			}

			b, err := json.Marshal(fileInfos)
			if err != nil {
				return err
			}

			w.Write(b)
			return nil
		}(); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	})

	ts := http.FileServer(http.Dir("./out"))
	http.HandleFunc("/api/ts", func(w http.ResponseWriter, r *http.Request) {
		if err := func() error {
			q := r.URL.Query()
			in, segment := q.Get("in"), q.Get("segment")
			if in == "" || !isAlphaNumeric(in) {
				return fmt.Errorf("invalid query: in %s", in)
			}
			if segment == "" {
				return fmt.Errorf("invalid query: segment %s", segment)
			}

			r.URL.Path = fmt.Sprintf("/%s/%s", in, segment)
			ts.ServeHTTP(w, r)
			return nil
		}(); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
	})

	http.Handle("/", http.FileServer(http.Dir(".")))

	fmt.Println("Server is running at http://localhost:9000")
	http.ListenAndServe(":9000", nil)
}
