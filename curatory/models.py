import json
# These are objects are designed to be immutable

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class JSONable:
    def to_json_obj(self):
        output = self.__dict__.copy()
        output['type'] = type(self).__name__
        return output

    def to_json_string(self):
        return json.dumps(self.to_json_obj())

    @classmethod
    def from_json_string(cls, obj):
        return cls.from_json_obj(json.loads(obj))

class Job(JSONable):
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'MutuallyExclusiveLabelJob':
            return \
                MutuallyExclusiveLabelJob(
                    obj['label_type'],
                    obj['images'],
                    obj['labels'],
                )
        elif obj['type'] == 'AuditLabelsJob':
            return \
                AuditLabelsJob(
                    obj['label_type'],
                    obj['images'],
                    obj['labels'],
                )
        elif obj['type'] == 'PickLocationJob':
            return \
                PickLocationJob(
                    obj['label_type'],
                    obj['images'],
                )
        else:
            raise TypeError()

class MutuallyExclusiveLabelJob(Job):
    def __init__(self, label_type, images, labels):
        self.label_type = label_type
        self.images = images
        self.labels = labels

    def questions(self):
        for image in self.images:
            yield LabelImageQuestion(self.label_type, image, self.labels)

    def collate_answers(self, questions, answers):
        results = {}
        for question, answer in zip(questions, answers):
            results[question.image] = answer.label
        return MutuallyExclusiveLabelResult(results)

class PickLocationJob(Job):
    def __init__(self, label_type, images):
        self.label_type = label_type
        self.images = images

    def questions(self):
        for image in self.images:
            yield PickLocationQuestion(self.label_type, image)

    def collate_answers(self, questions, answers):
        results = {}
        for question, answer in zip(questions, answers):
            results[question.image] = answer.location
        return PickLocationResult(results)

class AuditLabelsJob(Job):
    def __init__(self, label_type, images, labels):
        self.label_type = label_type
        self.images = images
        self.labels = labels

    def questions(self):
        groups = {}
        for image, label in zip(self.images, self.labels):
            groups[label] = groups.get(label, [])
            groups[label].append(image)
        for label, group in groups.items():
            for chunk in chunks(25, group):
                yield AuditLabelQuestion(self.label_type, label, chunk)

    def collate_answers(self, questions, answers):
        incorrect_images = set()
        for question, answer in zip(questions, answers):
            incorrect_images |= set(answer.incorrect_images)
        return AuditLabelsResult(list(incorrect_images))

class Question(JSONable):
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'LabelImageQuestion':
            return \
                LabelImageQuestion(
                    obj['label_type'],
                    obj['image'],
                    obj['labels'],
                )
        elif obj['type'] == 'PickLocationQuestion':
            return \
                PickLocationQuestion(
                    obj['label_type'],
                    obj['image'],
                )
        elif obj['type'] == 'AuditLabelQuestion':
            return \
                AuditLabelQuestion(
                    obj['label_type'],
                    obj['label'],
                    obj['images'],
                )
        else:
            raise TypeError()

class LabelImageQuestion(Question):
    def __init__(self, label_type, image, labels):
        self.label_type = label_type
        self.image = image
        self.labels = labels

class PickLocationQuestion(Question):
    def __init__(self, label_type, image):
        self.label_type = label_type
        self.image = image

class AuditLabelQuestion(Question):
    def __init__(self, label_type, label, images):
        self.label_type = label_type
        self.label = label
        self.images = images

class Answer(JSONable):
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'LabelAnswer':
            return LabelAnswer(obj['label'])
        elif obj['type'] == 'AuditAnswer':
            return AuditAnswer(obj['incorrect_images'])
        elif obj['type'] == 'PickLocationAnswer':
            return PickLocationAnswer(obj['location'])
        else:
            raise TypeError()

class LabelAnswer(Answer):
    def __init__(self, label):
        self.label = label

class PickLocationAnswer(Answer):
    def __init__(self, location):
        self.location = location

class AuditAnswer(Answer):
    def __init__(self, incorrect_images):
        self.incorrect_images = incorrect_images

class Result(JSONable):
    @classmethod
    def from_json_obj(cls, obj):
        if obj['type'] == 'MutuallyExclusiveLabelResult':
            return MutuallyExclusiveLabelResult(obj['labels'])
        elif obj['type'] == 'PickLocationResult':
            return PickLocationResult(obj['labels'])
        elif obj['type'] == 'AuditLabelsResult':
            return AuditLabelsResult(obj['incorrect_images'])
        else:
            raise TypeError()

class MutuallyExclusiveLabelResult(Result):
    def __init__(self, labels):
        self.labels = labels

class PickLocationResult(Result):
    def __init__(self, labels):
        self.labels = labels

class AuditLabelsResult(Result):
    def __init__(self, incorrect_images):
        self.incorrect_images = incorrect_images
