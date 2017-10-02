# These are objects are designed to be immutable

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Job:
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

    def to_json(self):
        return {
            'type': 'MutuallyExclusiveLabelJob',
            'label_type': self.label_type,
            'images': self.images,
            'labels': self.labels,
        }

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

    def to_json(self):
        return {
            'type': 'PickLocationJob',
            'label_type': self.label_type,
            'images': self.images,
        }

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

class Question:
    pass

class LabelImageQuestion(Question):
    def __init__(self, label_type, image, labels):
        self.label_type = label_type
        self.image = image
        self.labels = labels

    def to_json_obj(self):
        return {
            'type': 'LabelImageQuestion',
            'label_type': self.label_type,
            'image': self.image,
            'labels': self.labels,
        }

class PickLocationQuestion(Question):
    def __init__(self, label_type, image):
        self.label_type = label_type
        self.image = image

    def to_json_obj(self):
        return {
            'type': 'PickLocationQuestion',
            'label_type': self.label_type,
            'image': self.image,
        }

class AuditLabelQuestion(Question):
    def __init__(self, label_type, label, images):
        self.label_type = label_type
        self.label = label
        self.images = images

    def to_json_obj(self):
        return {
            'type': 'AuditLabelQuestion',
            'label_type': self.label_type,
            'label': self.label,
            'images': self.images,
        }

class Answer:
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

class Result:
    pass

class MutuallyExclusiveLabelResult(Result):
    def __init__(self, labels):
        self.labels = labels

    def to_json_obj(self):
        return {
            'type': 'MutuallyExclusiveLabelResult',
            'labels': self.labels,
        }

class PickLocationResult(Result):
    def __init__(self, labels):
        self.labels = labels

    def to_json_obj(self):
        return {
            'type': 'PickLocationResult',
            'labels': self.labels,
        }

class AuditLabelsResult(Result):
    def __init__(self, incorrect_images):
        self.incorrect_images = incorrect_images

    def to_json_obj(self):
        return {
            'type': 'AuditLabelsResult',
            'incorrect_images': self.incorrect_images,
        }
